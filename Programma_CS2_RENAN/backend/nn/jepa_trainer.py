import math
from typing import List, Optional

import torch
import torch.optim as optim

from Programma_CS2_RENAN.backend.nn.early_stopping import EmbeddingCollapseDetector
from Programma_CS2_RENAN.backend.nn.jepa_model import (
    ConceptLabeler,
    JEPACoachingModel,
    VLJEPACoachingModel,
    jepa_contrastive_loss,
    vicreg_regularization,
    vl_jepa_concept_loss,
)
from Programma_CS2_RENAN.backend.processing.validation.drift import (
    DriftMonitor,
    DriftReport,
    should_retrain,
)
from Programma_CS2_RENAN.observability.label_source_monitor import (
    LABEL_SOURCE_ROUND_STATS,
    LABEL_SOURCE_SKIPPED_NO_ROUND_STATS,
    LabelSourceMonitor,
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
        # Phase 4B: Linear warmup (5%) → cosine decay (Goyal et al. 2017)
        _warmup_epochs = max(1, int(t_max * 0.05))
        self.scheduler = optim.lr_scheduler.SequentialLR(
            self.optimizer,
            schedulers=[
                optim.lr_scheduler.LinearLR(
                    self.optimizer, start_factor=0.01, total_iters=_warmup_epochs
                ),
                optim.lr_scheduler.CosineAnnealingLR(
                    self.optimizer, T_max=max(1, t_max - _warmup_epochs)
                ),
            ],
            milestones=[_warmup_epochs],
        )

        # Phase 4A: Mixed precision (Micikevicius et al. 2018)
        self._device_type = "cuda" if torch.cuda.is_available() else "cpu"
        self._amp_enabled = torch.cuda.is_available()
        self._scaler = torch.amp.GradScaler(enabled=self._amp_enabled)

        # Phase 4C+D: Gradient accumulation (effective batch *= 4) and clipping
        self._accumulation_steps = 4
        self._max_grad_norm = 1.0

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

        # P9-02 (Phase 0 hygiene): hard-stop guard against embedding collapse.
        # Reads the per-batch variances accumulated by train_epoch and raises
        # EmbeddingCollapseError after two consecutive collapsed val epochs.
        # Per CS2_Coach_Modernization_Report.pdf §9 and Supplement_N260 §5.1.
        self.embedding_collapse_detector = EmbeddingCollapseDetector(threshold=0.01, patience=2)

        # G-01 (Phase 0 hygiene): structured telemetry for the concept-label
        # routing decision. train_step_vl reports `label_source` per batch;
        # this monitor sliding-windows the rate and alarms above 1% over 5min.
        # Per CS2_Coach_Modernization_Report.pdf §9 and Supplement_N260 §5.1 #3.
        self.label_source_monitor = LabelSourceMonitor()

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
        self,
        x_context: torch.Tensor,
        x_target: torch.Tensor,
        negatives: torch.Tensor,
        step_optimizer: bool = True,
    ) -> dict:
        """
        Single self-supervised training step with AMP + gradient accumulation.

        Args:
            step_optimizer: If True, unscale/clip/step/EMA after backward.
                If False, only accumulate gradients (for gradient accumulation).
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

        # Phase 2D: Tabular augmentation on context (target stays clean — BYOL paradigm)
        x_context_aug = self._tabular_augment(x_context)

        # Phase 4A: AMP autocast for forward + loss
        with torch.amp.autocast(device_type=self._device_type, enabled=self._amp_enabled):
            pred_embedding, target_embedding = self.model.forward_jepa_pretrain(
                x_context_aug, x_target
            )
            if negatives is not None and negatives.shape[-1] != pred_embedding.shape[-1]:
                negatives = self.encode_raw_negatives(negatives, x_context.shape[1])

            # Phase 2A: Augment negatives with MoCo queue
            negatives = self._augment_with_moco_queue(negatives, pred_embedding)

            # Phase 2B: Learned temperature (CLIP-style)
            tau = self.model.log_temperature.exp().clamp(0.01, 1.0)
            loss = jepa_contrastive_loss(pred_embedding, target_embedding, negatives, tau)

            # Phase 2E: VICReg regularization on pred embeddings
            vicreg = vicreg_regularization(pred_embedding, lambda_var=25.0, lambda_cov=1.0)
            loss = loss + 0.01 * vicreg

        # Phase 2A: Enqueue target embeddings for future negatives
        self.model.enqueue(target_embedding)

        # Phase 4C: Scale loss for gradient accumulation
        self._scaler.scale(loss / self._accumulation_steps).backward()

        grad_norm = None
        if step_optimizer:
            grad_norm = self._optimizer_step()

        embedding_variance = self._log_embedding_diversity(pred_embedding)

        return {
            "loss": loss.item(),
            "embedding_variance": embedding_variance,
            "grad_norm": grad_norm,
            "temperature": tau.item(),
            "vicreg": vicreg.item(),
        }

    @staticmethod
    def _tabular_augment(
        x: torch.Tensor, mask_ratio: float = 0.3, noise_std: float = 0.03
    ) -> torch.Tensor:
        """Phase 2D: Tabular multi-crop augmentation (TabNet-style feature masking)."""
        mask = torch.bernoulli(torch.full_like(x, 1.0 - mask_ratio))
        noise = torch.randn_like(x) * noise_std
        return x * mask + noise

    def _augment_with_moco_queue(
        self, negatives: torch.Tensor, pred_embedding: torch.Tensor
    ) -> torch.Tensor:
        """Phase 2A: Augment in-batch negatives with MoCo queue entries."""
        queue = self.model.moco_queue.clone().detach()
        b = pred_embedding.shape[0]
        # Sample subset from queue to keep memory bounded
        n_queue = min(64, queue.shape[0])
        idx = torch.randperm(queue.shape[0], device=queue.device)[:n_queue]
        queue_neg = queue[idx].unsqueeze(0).expand(b, -1, -1)  # (B, n_queue, latent_dim)
        if negatives is not None:
            return torch.cat([negatives, queue_neg], dim=1)
        return queue_neg

    def _optimizer_step(self) -> float:
        """Unscale → clip → step → scaler update → zero_grad → EMA."""
        self._scaler.unscale_(self.optimizer)
        trainable = [p for p in self.model.parameters() if p.requires_grad]
        grad_norm = torch.nn.utils.clip_grad_norm_(trainable, self._max_grad_norm).item()
        self._scaler.step(self.optimizer)
        self._scaler.update()
        self.optimizer.zero_grad()
        self.model.update_target_encoder(momentum=self._scheduled_ema_momentum())
        logger.debug("Grad norm: %.4f", grad_norm)
        return grad_norm

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

        P9-02: at end-of-epoch, the mean of per-batch embedding variances is
        fed to ``self.embedding_collapse_detector``, which raises
        ``EmbeddingCollapseError`` after two consecutive collapsed epochs
        (variance < 0.01). The error propagates out of train_epoch — callers
        must let it bubble so training aborts rather than silently continuing
        on a degenerate encoder.
        """
        total_loss = 0
        count = 0
        epoch_variances: List[float] = []

        self.optimizer.zero_grad()
        accum = self._accumulation_steps

        for batch_idx, batch in enumerate(dataloader):
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
            indices = torch.arange(batch_size, device=device)
            negatives_tensor = torch.stack(
                [all_encoded[indices != i] for i in range(batch_size)]
            )  # [B, B-1, latent]

            do_step = (count + 1) % accum == 0
            result = self.train_step(x_context, x_target, negatives_tensor, step_optimizer=do_step)
            total_loss += result["loss"]
            count += 1

            v = result.get("embedding_variance")
            if v is not None:
                epoch_variances.append(float(v))

        # Flush any remaining accumulated gradients
        if count % accum != 0:
            self._optimizer_step()

        self.scheduler.step()

        # NN-TR-02: Warn if dataloader was empty (no batches processed)
        if count == 0:
            logger.warning(
                "NN-TR-02: train_epoch completed with 0 batches — dataloader may be empty"
            )

        # P9-02 hard-stop check. update() raises EmbeddingCollapseError when
        # the consecutive-collapsed counter reaches patience (default 2);
        # training aborts via the propagated exception.
        if epoch_variances:
            epoch_mean_variance = sum(epoch_variances) / len(epoch_variances)
            logger.info(
                "Epoch embedding variance: mean=%.6f over %d batches",
                epoch_mean_variance,
                len(epoch_variances),
            )
            self.embedding_collapse_detector.update(epoch_mean_variance)

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

        # Reset LR scheduler with warmup for fresh training
        _warmup = max(1, int(epochs * 0.05))
        self.scheduler = optim.lr_scheduler.SequentialLR(
            self.optimizer,
            schedulers=[
                optim.lr_scheduler.LinearLR(self.optimizer, start_factor=0.01, total_iters=_warmup),
                optim.lr_scheduler.CosineAnnealingLR(
                    self.optimizer, T_max=max(1, epochs - _warmup)
                ),
            ],
            milestones=[_warmup],
        )

        # V-3 FIX: Reset EMA cosine momentum schedule for fresh retraining.
        # Without this, _ema_step accumulates from previous training, causing
        # progress > 1.0 (clamped) → momentum ≈ 1.0 (frozen target encoder).
        self._ema_step = 0
        self._ema_total_steps = epochs * len(full_dataloader)

        # P9-02: clear consecutive-collapse counter so a prior near-collapse
        # state does not abort retraining on the very first new epoch.
        self.embedding_collapse_detector.reset()

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
        step_optimizer: bool = True,
    ) -> dict:
        """
        VL-JEPA training step: InfoNCE + concept alignment + diversity.
        AMP and gradient accumulation via step_optimizer flag.
        """
        if not isinstance(self.model, VLJEPACoachingModel):
            raise TypeError("train_step_vl requires a VLJEPACoachingModel")

        self.model.train()

        # Phase 2D: Tabular augmentation
        x_context_aug = self._tabular_augment(x_context)

        # Phase 4A: AMP autocast
        with torch.amp.autocast(device_type=self._device_type, enabled=self._amp_enabled):
            pred_embedding, target_embedding = self.model.forward_jepa_pretrain(
                x_context_aug,
                x_target,
            )
            if negatives is not None and negatives.shape[-1] != pred_embedding.shape[-1]:
                negatives = self.encode_raw_negatives(negatives, x_context.shape[1])
            negatives = self._augment_with_moco_queue(negatives, pred_embedding)
            tau = self.model.log_temperature.exp().clamp(0.01, 1.0)
            infonce_loss = jepa_contrastive_loss(
                pred_embedding,
                target_embedding,
                negatives,
                tau,
            )
            infonce_loss = infonce_loss + 0.01 * vicreg_regularization(pred_embedding)
            vl_output = self.model.forward_vl(x_context_aug)
            concept_logits = vl_output["concept_logits"]

        self.model.enqueue(target_embedding)

        labeler = ConceptLabeler()
        valid_indices: list[int] = []
        if round_stats is not None and any(rs is not None for rs in round_stats):
            batch_labels = []
            for idx, rs in enumerate(round_stats):
                if rs is not None:
                    batch_labels.append(labeler.label_from_round_stats(rs))
                    valid_indices.append(idx)
            if not batch_labels:
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
            if not getattr(self, "_concept_skip_logged", False):
                logger.warning(
                    "J-2: VL-JEPA concept alignment SKIPPED — no RoundStats available. "
                    "InfoNCE loss will be used alone (no label leakage risk)."
                )
                self._concept_skip_logged = True

            self._scaler.scale(infonce_loss / self._accumulation_steps).backward()
            if step_optimizer:
                self._optimizer_step()
            self.label_source_monitor.record(LABEL_SOURCE_SKIPPED_NO_ROUND_STATS)
            return {
                "total_loss": infonce_loss.item(),
                "infonce_loss": infonce_loss.item(),
                "concept_loss": 0.0,
                "diversity_loss": 0.0,
                "label_source": LABEL_SOURCE_SKIPPED_NO_ROUND_STATS,
            }

        with torch.amp.autocast(device_type=self._device_type, enabled=self._amp_enabled):
            concept_total, concept_loss, diversity_loss = vl_jepa_concept_loss(
                concept_logits,
                concept_labels,
                self.model.concept_embeddings.weight,
                alpha=concept_alpha,
                beta=concept_beta,
            )
            total_loss = infonce_loss + concept_total

        self._scaler.scale(total_loss / self._accumulation_steps).backward()
        if step_optimizer:
            self._optimizer_step()

        self.label_source_monitor.record(LABEL_SOURCE_ROUND_STATS)

        return {
            "total_loss": total_loss.item(),
            "infonce_loss": infonce_loss.item(),
            "concept_loss": concept_loss.item(),
            "diversity_loss": diversity_loss.item(),
            "label_source": LABEL_SOURCE_ROUND_STATS,
        }
