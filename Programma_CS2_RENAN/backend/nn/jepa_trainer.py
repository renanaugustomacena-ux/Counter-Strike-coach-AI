import math
from typing import List, Optional

import torch
import torch.optim as optim

from Programma_CS2_RENAN.backend.nn.jepa_model import (
    ConceptLabeler,
    JEPACoachingModel,
    VLJEPACoachingModel,
    jepa_contrastive_loss,
    vl_jepa_concept_loss,
)
from Programma_CS2_RENAN.backend.processing.validation.drift import (
    DriftMonitor,
    DriftReport,
    should_retrain,
)
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.jepa_trainer")


class JEPATrainer:
    """
    Trainer for JEPA (Joint-Embedding Predictive Architecture).
    Handles self-supervised pre-training with drift-triggered retraining (Task 2.19.3).
    """

    def __init__(
        self,
        model: JEPACoachingModel,
        lr: float = 1e-4,
        weight_decay: float = 1e-2,  # J-7: Loshchilov & Hutter (ICLR 2019) AdamW default
        drift_threshold: float = 2.5,
        t_max: int = 100,
    ):
        self.model = model
        # NN-36: Exclude target encoder (EMA-only, never receives gradients)
        for n, p in model.named_parameters():
            if "target_encoder" in n:
                p.requires_grad = False

        # KT-05: Separate concept parameters for 0.05x LR multiplier
        # (VL-JEPA paper Section 4.6 — prevents concept embedding collapse)
        concept_params = []
        other_params = []
        for n, p in model.named_parameters():
            if not p.requires_grad:
                continue
            if "concept" in n:
                concept_params.append(p)
            else:
                other_params.append(p)

        if concept_params:
            param_groups = [
                {"params": other_params},
                {"params": concept_params, "lr": lr * 0.05},
            ]
            self.optimizer = optim.AdamW(param_groups, lr=lr, weight_decay=weight_decay)
        else:
            trainable = [p for p in model.parameters() if p.requires_grad]
            self.optimizer = optim.AdamW(trainable, lr=lr, weight_decay=weight_decay)
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=t_max)

        # J-6: EMA cosine momentum schedule (Assran et al., CVPR 2023, Section 3.2).
        # τ(t) = 1 - (1 - τ_base) · (cos(πt/T) + 1) / 2
        # Starts at 0.996 (fast tracking) → 1.0 (frozen target) over training.
        self._ema_base_momentum: float = 0.996
        # REPR-01: if load_jepa_model attached saved counters to the model,
        # rehydrate them so the cosine schedule resumes at the correct τ
        # instead of restarting at τ=0.996.
        self._ema_step: int = int(getattr(model, "_saved_ema_step", 0))
        self._ema_total_steps: int = int(getattr(model, "_saved_ema_total_steps", t_max))

        # Task 2.19.3: Drift monitoring for automatic retraining
        self.drift_monitor = DriftMonitor(z_threshold=drift_threshold)
        self.drift_history: List[DriftReport] = []
        self._needs_full_retrain = False
        self._reference_stats: Optional[dict] = None

    def set_total_steps(self, epochs: int, batches_per_epoch: int) -> None:
        """Set actual total training steps for EMA schedule (NN-04b)."""
        self._ema_total_steps = max(1, epochs * batches_per_epoch)

    def _scheduled_ema_momentum(self) -> float:
        """Compute EMA momentum from cosine schedule (J-6).

        Assran et al. (CVPR 2023), Section 3.2:
            τ(t) = 1 - (1 - τ_base) · (cos(πt/T) + 1) / 2

        At t=0: τ = τ_base (0.996) — target tracks context quickly.
        At t=T: τ → 1.0 — target freezes for maximum stability.
        """
        progress = min(self._ema_step / max(1, self._ema_total_steps), 1.0)
        momentum = 1.0 - (1.0 - self._ema_base_momentum) * (math.cos(math.pi * progress) + 1) / 2
        self._ema_step += 1
        return momentum

    def encode_raw_negatives(self, negatives: torch.Tensor, seq_len: int) -> torch.Tensor:
        """Encode raw feature negatives into latent space (NN-H-02).

        Shared by both training and validation paths to ensure identical
        encoding logic. Each negative is expanded to a full sequence, encoded
        by the target encoder, then mean-pooled over the temporal dimension.

        Args:
            negatives: Raw features, shape (B, N, feat_dim)
            seq_len: Context sequence length to expand negatives to

        Returns:
            Encoded negatives, shape (B, N, latent_dim)
        """
        with torch.no_grad():
            b, n, d = negatives.shape
            neg_seqs = negatives.reshape(b * n, 1, d)
            neg_seqs = neg_seqs.expand(-1, seq_len, -1)
            neg_encoded = self.model.target_encoder(neg_seqs).mean(dim=1)
            return neg_encoded.reshape(b, n, -1)

    def train_step(
        self, x_context: torch.Tensor, x_target: torch.Tensor, negatives: torch.Tensor
    ) -> dict:
        """
        Single self-supervised training step.

        Returns dict with "loss" key for consistency with RAPTrainer and VL-JEPA interfaces.

        Handles two negative-sample paths:
        1. Pre-encoded negatives (from train_epoch dataloader) — shape (B, N, latent_dim)
        2. Raw feature negatives (from TrainingOrchestrator._prepare_batch) — shape (B, N, METADATA_DIM)
           These are auto-detected by dimension mismatch and encoded via target_encoder.
        """
        # NN-TR-03: Validate input tensor shapes before forward pass
        if x_context.ndim != 3:
            raise ValueError(
                f"NN-TR-03: x_context must be 3D (B, seq_len, input_dim), got {x_context.ndim}D"
            )
        if x_target.ndim != 3:
            raise ValueError(
                f"NN-TR-03: x_target must be 3D (B, seq_len, input_dim), got {x_target.ndim}D"
            )
        if x_context.shape[0] != x_target.shape[0]:
            raise ValueError(
                f"NN-TR-03: batch size mismatch: context={x_context.shape[0]}, target={x_target.shape[0]}"
            )

        # NN-JT-03: Ensure input tensors are on the model's device
        device = next(self.model.parameters()).device
        x_context = x_context.to(device)
        x_target = x_target.to(device)
        if negatives is not None:
            negatives = negatives.to(device)

        self.model.train()
        self.optimizer.zero_grad()

        # 1. Forward Pass
        pred_embedding, target_embedding = self.model.forward_jepa_pretrain(x_context, x_target)

        # 2. Encode raw negatives if from orchestrator batch (dimension mismatch = raw features)
        if negatives is not None and negatives.shape[-1] != pred_embedding.shape[-1]:
            negatives = self.encode_raw_negatives(negatives, x_context.shape[1])

        # 3. Compute Loss
        loss = jepa_contrastive_loss(pred_embedding, target_embedding, negatives)

        # 4. Optimization
        loss.backward()
        self.optimizer.step()

        # 5. Update Target Encoder (EMA with cosine momentum schedule — J-6)
        self.model.update_target_encoder(momentum=self._scheduled_ema_momentum())

        # 6. Embedding diversity monitoring (P9-02 acceptance criterion)
        embedding_variance = self._log_embedding_diversity(pred_embedding)

        return {"loss": loss.item(), "embedding_variance": embedding_variance}

    def _log_embedding_diversity(self, embeddings: torch.Tensor) -> float:
        """Monitor embedding collapse risk (P9-02 acceptance criterion).

        Returns the mean variance across latent dimensions. A healthy value
        should be > 0.01; below that indicates potential representation collapse.
        """
        with torch.no_grad():
            if embeddings.shape[0] < 2:
                return 0.0
            variance = embeddings.var(dim=0).mean().item()
            if variance < 0.01:
                logger.warning(
                    "JEPA embedding variance=%.6f — potential collapse detected", variance
                )
            else:
                logger.debug("JEPA embedding variance=%.6f (healthy)", variance)
            return variance

    def train_epoch(self, dataloader, device):
        """
        Train for one epoch.
        """
        total_loss = 0
        count = 0

        for batch in dataloader:
            x_context = batch["context"].to(device)
            x_target = batch["target"].to(device)

            # In-batch negatives: encode all targets once, then exclude self (NN-35 fix)
            batch_size = x_target.size(0)

            # NN-JT-01: In-batch negatives require batch_size > 1 (can't exclude self
            # from a single-element batch). Skip training on degenerate batches.
            if batch_size < 2:
                logger.debug(
                    "NN-JT-01: Skipping batch with size %d (need >= 2 for negatives)", batch_size
                )
                continue

            with torch.no_grad():
                all_encoded = self.model.target_encoder(x_target).mean(dim=1)  # [B, latent]

            # NN-TR-01: O(B²) negative construction — each sample excludes itself.
            # For typical batch sizes (32–128) this is fast. For B > 256 consider
            # vectorised masking: mask = ~torch.eye(B, dtype=bool, device=device)
            indices = torch.arange(batch_size, device=device)
            negatives_tensor = torch.stack(
                [all_encoded[indices != i] for i in range(batch_size)]
            )  # [B, B-1, latent]

            result = self.train_step(x_context, x_target, negatives_tensor)
            total_loss += result["loss"]
            count += 1

        # Step scheduler once per epoch (not per batch)
        self.scheduler.step()

        # NN-TR-02: Warn if dataloader was empty (no batches processed)
        if count == 0:
            logger.warning(
                "NN-TR-02: train_epoch completed with 0 batches — dataloader may be empty"
            )

        return total_loss / max(1, count)

    def check_val_drift(self, val_df, reference_stats: Optional[dict] = None):
        """
        Check validation set for feature drift and update retraining flag.

        Args:
            val_df: Validation DataFrame with feature columns.
            reference_stats: Optional reference statistics. If None, uses stored reference.
        """
        if reference_stats is None:
            if self._reference_stats is None:
                logger.warning("No reference stats available for drift check — skipping")
                return
            reference_stats = self._reference_stats
        else:
            self._reference_stats = reference_stats

        report = self.drift_monitor.check_drift(val_df, reference_stats)
        self.drift_history.append(report)

        logger.info(
            "Drift check: is_drifted=%s, max_z=%.2f, drifted_features=%s",
            report.is_drifted,
            report.max_z_score,
            report.drifted_features,
        )

        # Check if retraining should be triggered
        if should_retrain(self.drift_history, window=5):
            self._needs_full_retrain = True
            logger.warning("Drift threshold exceeded — flagging for full retraining")

    def retrain_if_needed(self, full_dataloader, device, epochs: int = 10):
        """
        Conditionally retrain model if drift flag is set.

        Args:
            full_dataloader: Full dataset loader for retraining.
            device: Training device.
            epochs: Number of epochs for full retraining.

        Returns:
            True if retraining occurred, False otherwise.
        """
        if not self._needs_full_retrain:
            return False

        logger.warning("Starting full model retraining due to detected drift")

        # Reset learning rate scheduler for fresh training
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=epochs)

        # V-3 FIX: Reset EMA cosine momentum schedule for fresh retraining.
        # Without this, _ema_step accumulates from previous training, causing
        # progress > 1.0 (clamped) → momentum ≈ 1.0 (frozen target encoder).
        self._ema_step = 0
        self._ema_total_steps = epochs * len(full_dataloader)

        for epoch in range(epochs):
            avg_loss = self.train_epoch(full_dataloader, device)
            logger.info("Retrain epoch %d/%d: loss=%.4f", epoch + 1, epochs, avg_loss)

        # Clear drift flag and history after successful retraining
        self._needs_full_retrain = False
        self.drift_history.clear()
        logger.info("Retraining complete — drift flag cleared")

        return True

    def train_step_vl(
        self,
        x_context: torch.Tensor,
        x_target: torch.Tensor,
        negatives: torch.Tensor,
        concept_alpha: float = 0.5,
        concept_beta: float = 0.1,
        round_stats=None,
    ) -> dict:
        """
        VL-JEPA training step: InfoNCE + concept alignment + diversity.

        Requires self.model to be a VLJEPACoachingModel instance.

        Args:
            x_context: Context window [batch, context_len, input_dim]
            x_target: Target window [batch, target_len, input_dim]
            negatives: Negative samples [batch, num_negatives, latent_dim]
            concept_alpha: Weight for concept alignment loss
            concept_beta: Weight for diversity regularization
            round_stats: Optional list of RoundStats objects for outcome-based labeling (G-01)

        Returns:
            Dict with infonce_loss, concept_loss, diversity_loss, total_loss
        """
        if not isinstance(self.model, VLJEPACoachingModel):
            raise TypeError("train_step_vl requires a VLJEPACoachingModel")

        self.model.train()
        self.optimizer.zero_grad()

        # 1. Standard JEPA pre-training forward
        pred_embedding, target_embedding = self.model.forward_jepa_pretrain(
            x_context,
            x_target,
        )

        # 2. InfoNCE contrastive loss
        infonce_loss = jepa_contrastive_loss(
            pred_embedding,
            target_embedding,
            negatives,
        )

        # 3. Concept alignment: encode context and get concept logits
        vl_output = self.model.forward_vl(x_context)
        concept_logits = vl_output["concept_logits"]

        # 4. Generate concept labels — prefer outcome-based (G-01 fix) over heuristic
        labeler = ConceptLabeler()
        valid_indices: list[int] = []
        if round_stats is not None and any(rs is not None for rs in round_stats):
            # G-01: Use RoundStats outcome data (no label leakage)
            # LEAK-02 fix: drop samples with rs=None instead of substituting
            # torch.full((16,), 0.5) — 0.5 under BCE-with-logits acts as a weak
            # positive for every concept simultaneously, producing incoherent
            # gradients. Mask via index selection and recompute logits slice.
            batch_labels = []
            for idx, rs in enumerate(round_stats):
                if rs is not None:
                    batch_labels.append(labeler.label_from_round_stats(rs))
                    valid_indices.append(idx)
            if not batch_labels:
                # Degenerate: all None after the any() check raced (should not
                # happen, but guard anyway). Fall through to skip path.
                concept_labels = None
            else:
                concept_labels = torch.stack(batch_labels).to(x_context.device)
                if len(valid_indices) < concept_logits.shape[0]:
                    idx_t = torch.tensor(
                        valid_indices, dtype=torch.long, device=concept_logits.device
                    )
                    concept_logits = concept_logits.index_select(0, idx_t)
        else:
            concept_labels = None

        if concept_labels is None:
            # J-2 FIX: Hard-gate heuristic fallback — skip concept alignment entirely.
            # The heuristic labeler (label_batch/label_tick) derives labels directly from
            # the input feature vector, causing label leakage: the model can learn a
            # near-linear mapping (concept[0] ≈ 0.5 + features[8]) instead of actual
            # coaching concepts. InfoNCE loss alone is sufficient for JEPA pre-training;
            # concept alignment is an additive enhancement that requires outcome labels.
            if not getattr(self, "_concept_skip_logged", False):
                logger.warning(
                    "J-2: VL-JEPA concept alignment SKIPPED — no RoundStats available. "
                    "InfoNCE loss will be used alone (no label leakage risk)."
                )
                self._concept_skip_logged = True

            # Return InfoNCE loss only, no concept alignment
            total_loss = infonce_loss
            total_loss.backward()
            self.optimizer.step()
            self.model.update_target_encoder(momentum=self._scheduled_ema_momentum())
            return {
                "total_loss": total_loss.item(),
                "infonce_loss": infonce_loss.item(),
                "concept_loss": 0.0,
                "diversity_loss": 0.0,
            }

        # 5. Concept loss + diversity
        concept_total, concept_loss, diversity_loss = vl_jepa_concept_loss(
            concept_logits,
            concept_labels,
            self.model.concept_embeddings.weight,
            alpha=concept_alpha,
            beta=concept_beta,
        )

        # 6. Combined loss
        total_loss = infonce_loss + concept_total

        # 7. Backward + optimize
        total_loss.backward()
        self.optimizer.step()
        # Note: scheduler.step() is called once per epoch in train_epoch(), not per batch

        # 8. EMA update for target encoder (cosine schedule — J-6)
        self.model.update_target_encoder(momentum=self._scheduled_ema_momentum())

        return {
            "total_loss": total_loss.item(),
            "infonce_loss": infonce_loss.item(),
            "concept_loss": concept_loss.item(),
            "diversity_loss": diversity_loss.item(),
        }
