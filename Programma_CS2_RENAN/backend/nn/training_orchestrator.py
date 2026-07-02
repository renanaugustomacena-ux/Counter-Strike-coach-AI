import logging

import numpy as np
import torch

from Programma_CS2_RENAN.backend.nn.config import GLOBAL_SEED, get_device
from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError, load_nn, save_nn
from Programma_CS2_RENAN.backend.nn.training_callbacks import CallbackRegistry
from Programma_CS2_RENAN.backend.storage.db_models import DatasetSplit
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.orchestrator")


def _flush_all_loggers() -> None:
    """Force-flush all logging handlers to prevent silent loss on process kill."""
    for handler in logging.root.handlers:
        handler.flush()
    for handler in logger.handlers:
        handler.flush()


class TrainingOrchestrator:
    """
    Unified Orchestrator for managing the details of the training lifecycle.

    Supported model types:
      - "jepa" / "vl-jepa": Self-supervised pre-training. Always available (pure PyTorch).
      - "rap": Experimental RAP Coach. Requires USE_RAP_MODEL=True + ncps + hflayers.
      - "rap-lite": Lightweight RAP variant. Requires USE_RAP_MODEL=True (pure PyTorch).

    Implements: Epoch Loop, Validation frequency, Early Stopping,
    Checkpointing (Best/Latest), Learning Rate Scheduling,
    Real-time Progress Reporting.
    """

    _DEFAULT_TRAIN_SAMPLES = 50_000
    _DEFAULT_VAL_SAMPLES = 10_000

    def __init__(
        self,
        manager,
        model_type="jepa",
        max_epochs=100,
        patience=10,
        batch_size=32,
        callbacks: CallbackRegistry = None,
        accumulation_steps: int = 4,
        train_samples: int | None = None,
        val_samples: int | None = None,
        dry_run: bool = False,
    ):
        self.manager = manager
        self.model_type = model_type
        self.max_epochs = max_epochs
        self.patience = patience
        self.batch_size = batch_size
        self._accumulation_steps = accumulation_steps
        # B4: dry-run is a non-destructive pipeline-integrity probe. It must NOT
        # write production checkpoints — the entry point already promises "will
        # NOT save production weights", but that contract was never threaded into
        # the orchestrator, so a `--dry-run` previously overwrote the real
        # `<model_name>.pt`/`_latest.pt` with a 1-epoch model (Law 7 violation).
        # When True, _run_epoch_loop skips every save_nn call.
        self.dry_run = dry_run

        from Programma_CS2_RENAN.core.config import get_setting

        self._train_samples = train_samples or get_setting(
            "TRAIN_SAMPLES", default=self._DEFAULT_TRAIN_SAMPLES
        )
        self._val_samples = val_samples or get_setting(
            "VAL_SAMPLES", default=self._DEFAULT_VAL_SAMPLES
        )
        self.device = get_device()
        self.best_val_loss = float("inf")
        self.patience_counter = 0
        self.callbacks = callbacks or CallbackRegistry()
        # Deterministic RNG for JEPA negative sampling (F3-02).
        # Seeded once at construction so training runs are reproducible.
        self._neg_rng = np.random.default_rng(seed=42)
        # NN-H-03: Cross-match negative pool for contrastive learning.
        # Stores feature vectors from previous batches so negatives come from
        # different matches, not the same temporal sequence as context/target.
        self._neg_pool: list = []
        _NEG_POOL_MAX = 500  # Max features retained across batches
        self._neg_pool_max = _NEG_POOL_MAX
        # W1.6: negatives per JEPA sample (named — was a magic 5 at the sampling
        # site) and a one-shot flag so the warmup→pool transition logs exactly once.
        self._n_contrastive_negatives = 5
        self._neg_pool_ready_logged = False
        # F3-11: Aggregate zero-tensor fallback counters across entire training run
        self._total_samples = 0
        self._total_fallbacks = 0
        self._current_epoch = 0
        _LTC_CURRICULUM_EPOCHS = 5
        self._ltc_curriculum_epochs = _LTC_CURRICULUM_EPOCHS

        # Determine internal model/trainer classes based on type
        if model_type in ("jepa", "vl-jepa"):
            from Programma_CS2_RENAN.backend.nn.jepa_trainer import JEPATrainer

            self.TrainerClass = JEPATrainer
            self.model_name = "vl_jepa_brain" if model_type == "vl-jepa" else "jepa_brain"
            self.learning_rate = 1e-4
            self._use_vl = model_type == "vl-jepa"

        elif model_type == "rap":
            from Programma_CS2_RENAN.core.config import get_setting

            if not get_setting("USE_RAP_MODEL", default=False):
                raise ValueError(
                    "RAP model training is experimental and disabled by default. "
                    "Enable via USE_RAP_MODEL=True in settings."
                )
            from Programma_CS2_RENAN.backend.nn.experimental.rap_coach.trainer import RAPTrainer

            self.TrainerClass = RAPTrainer
            self.model_name = "rap_coach"
            self.learning_rate = 5e-5
            self._use_vl = False
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def _warn_no_gpu(self):
        """Emit GPU-absent warning so user knows training will be slow."""
        if torch.cuda.is_available():
            return
        logger.warning(
            "No NVIDIA GPU detected. Training will run on CPU and may be "
            "10-50x slower. For faster training, use a machine with an NVIDIA GPU."
        )
        try:
            from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

            get_state_manager().add_notification(
                "training", "WARNING", "Training on CPU (no GPU detected). This will be slow."
            )
        except Exception:
            pass

    def _load_or_init_model(self):
        """Create model via Factory and load checkpoint if available.

        REPR-01: EMA step counters rehydrate via model attributes set by
        ``jepa_train.load_jepa_model`` (``_saved_ema_step``, ``_saved_ema_total_steps``).
        Note: the orchestrator save path (``persistence.save_nn``) stores
        ``state_dict`` only — EMA counters persist through ``jepa_train``'s
        separate checkpoint format.  ``set_total_steps`` later recomputes
        ``_ema_total_steps`` from the current run config.

        B3.2: ``best_val_loss`` is restored from the sidecar ``extra`` field
        so resume compares against the checkpoint's stored best, not +inf.
        """
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        model = ModelFactory.get_model(self.model_type).to(self.device)
        try:
            load_nn(self.model_name, model)
            logger.info("Resumed training from %s", self.model_name)
            self._restore_best_val_from_sidecar()
        except FileNotFoundError:
            logger.info("No checkpoint found — starting fresh training for %s", self.model_name)
        except StaleCheckpointError:
            logger.warning(
                "Stale checkpoint for %s — architecture changed. Starting fresh training.",
                self.model_name,
            )
        except Exception as e:
            logger.warning(
                "Checkpoint load failed for %s (possible corruption): %s. Starting fresh.",
                self.model_name,
                e,
            )
        return model

    def _restore_best_val_from_sidecar(self):
        """B3.2: Restore best_val_loss from checkpoint sidecar on resume.

        Without this, resume seeds best_val_loss with +inf, causing the first
        epoch to always declare 'new best' and overwrite the prior checkpoint
        even if the resumed model performs worse.
        """
        import json

        from Programma_CS2_RENAN.backend.nn.persistence import _sidecar_path, get_model_path

        try:
            path = get_model_path(self.model_name, user_id=None)
            sidecar = _sidecar_path(path)
            if sidecar.exists():
                meta = json.loads(sidecar.read_text())
                stored = (meta.get("extra") or {}).get("best_val_loss")
                if stored is not None:
                    self.best_val_loss = float(stored)
                    logger.info(
                        "B3.2: Restored best_val_loss=%.6f from sidecar", self.best_val_loss
                    )
        except Exception as e:
            logger.debug("B3.2: Could not restore best_val_loss from sidecar: %s", e)

    def _run_epoch_loop(self, trainer, model, val_data, context):
        """Execute the train/validate/checkpoint epoch loop. Returns final epoch number.

        B1: Train data is re-fetched each epoch with ``seed = GLOBAL_SEED + epoch``
        so the subsample window slides across the corpus.  Val data stays fixed
        (passed in) so early-stopping comparisons remain stable across epochs.
        """
        final_epoch = 0
        for epoch in range(1, self.max_epochs + 1):
            final_epoch = epoch
            self._current_epoch = epoch
            if context:
                context.check_state()

            self.callbacks.fire("on_epoch_start", epoch=epoch)

            train_data = self._fetch_batches(is_train=True, epoch=epoch)
            if not train_data:
                logger.warning("B1: Empty train data at epoch %d — stopping", epoch)
                break

            train_loss = self._run_epoch(trainer, train_data, is_train=True, context=context)

            if val_data:
                val_loss = self._run_epoch(trainer, val_data, is_train=False, context=context)
            else:
                val_loss = train_loss
                if epoch == 1:
                    logger.warning(
                        "No validation data — overfitting detection disabled (val_loss = train_loss)"
                    )

            if hasattr(trainer, "scheduler") and trainer.scheduler is not None:
                trainer.scheduler.step()

            self._report_progress(epoch, train_loss, val_loss)

            self.callbacks.fire(
                "on_epoch_end",
                epoch=epoch,
                train_loss=train_loss,
                val_loss=val_loss,
                model=model,
                optimizer=trainer.optimizer if hasattr(trainer, "optimizer") else None,
            )

            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.patience_counter = 0
                # B4: best-val/patience state is tracked even in dry-run so
                # early-stopping behaviour is identical; only the disk write is
                # suppressed.
                if self.dry_run:
                    logger.info(
                        "DRY RUN: new best (val %s) — checkpoint save skipped",
                        format(val_loss, ".6f"),
                    )
                else:
                    save_nn(
                        model,
                        self.model_name,
                        user_id=None,
                        extra_meta={"best_val_loss": val_loss},
                    )
                    logger.info("New Best Model Saved (Val Loss: %s)", format(val_loss, ".6f"))
            else:
                self.patience_counter += 1

            if not self.dry_run:
                save_nn(model, f"{self.model_name}_latest", user_id=None)
            _flush_all_loggers()

            if self.patience_counter >= self.patience:
                logger.info("Early Stopping Triggered at Epoch %s", epoch)
                _flush_all_loggers()
                break

        return final_epoch

    def _finalize_training(self, model, final_epoch):
        """Post-loop gates and on_train_end callback."""
        if self._total_samples > 0 and self._total_fallbacks > 0:
            rate = self._total_fallbacks / self._total_samples * 100
            if rate > 30:
                logger.error(
                    "P3-C: Training ABORTED — aggregate zero-tensor fallback rate %.1f%% "
                    "(%d/%d samples) exceeds 30%% threshold. Match databases may be missing.",
                    rate,
                    self._total_fallbacks,
                    self._total_samples,
                )
                return
            level = logger.warning if rate > 10 else logger.info
            level(
                "Training complete — zero-tensor fallback rate: %.1f%% (%d/%d samples)",
                rate,
                self._total_fallbacks,
                self._total_samples,
            )

        self.callbacks.fire(
            "on_train_end",
            model=model,
            final_metrics={
                "best_val_loss": self.best_val_loss,
                "final_epoch": final_epoch,
                "model_type": self.model_type,
                "fallback_rate": (
                    self._total_fallbacks / max(self._total_samples, 1)
                    if self._total_samples > 0
                    else 0.0
                ),
            },
        )
        logger.info("Training Cycle Complete.")

    def run_training(self, context=None):
        """Execute the full training pipeline."""
        logger.info("Orchestrator Starting: %s Cycle", self.model_name.upper())
        self._warn_no_gpu()

        from Programma_CS2_RENAN.backend.nn.data_quality import run_pre_training_quality_check

        quality_report = run_pre_training_quality_check()
        if not quality_report.passed:
            logger.error(
                "P3-D: Training ABORTED — pre-training quality check FAILED.\n%s",
                quality_report.summary(),
            )
            return

        model = self._load_or_init_model()

        trainer_kwargs = {"lr": self.learning_rate}
        if self.model_type in ("jepa", "vl-jepa", "rap"):
            trainer_kwargs["t_max"] = self.max_epochs
        if self.model_type == "rap":
            trainer_kwargs["accumulation_steps"] = self._accumulation_steps
        trainer = self.TrainerClass(model, **trainer_kwargs)

        # B1: Pre-flight probe — verify data availability and log counts.
        # This uses epoch=0 (seed=42); actual training re-fetches per epoch
        # with rotating seeds so each epoch sees a fresh subsample.
        preflight_train = self._fetch_batches(is_train=True, epoch=0)
        val_data = self._fetch_batches(is_train=False, epoch=0)

        if not preflight_train:
            logger.warning("Training Aborted: Insufficient Training Data")
            return

        total_train_samples = len(preflight_train) * self.batch_size
        _MIN_TRAINING_SAMPLES = 100
        if total_train_samples < _MIN_TRAINING_SAMPLES:
            logger.error(
                "P3-C: Training aborted — only %d samples (minimum %d required). "
                "Ingest more demos before training.",
                total_train_samples,
                _MIN_TRAINING_SAMPLES,
            )
            return

        logger.info(
            "B2: Training on ~%d samples/epoch (cap=%d, rotated), "
            "Validating on %d (cap=%d, fixed)",
            total_train_samples,
            self._train_samples,
            len(val_data) * self.batch_size if val_data else 0,
            self._val_samples,
        )

        self.callbacks.fire(
            "on_train_start",
            model=model,
            config={
                "model_type": self.model_type,
                "max_epochs": self.max_epochs,
                "batch_size": self.batch_size,
                "lr": self.learning_rate,
            },
        )

        if hasattr(trainer, "set_total_steps"):
            import math as _math

            steps_per_epoch = _math.ceil(len(preflight_train) / self._accumulation_steps)
            trainer.set_total_steps(self.max_epochs, steps_per_epoch)

        final_epoch = self._run_epoch_loop(trainer, model, val_data, context)
        self._finalize_training(model, final_epoch)

    def _fetch_batches(self, is_train=True, epoch=0):
        """Fetch and batch data from Manager.

        B1: For JEPA, ``epoch`` drives per-epoch seed rotation so each epoch
        sees a different subsample of the tick corpus.  Val uses epoch=0
        (fixed seed) so early-stopping comparisons remain stable.
        """
        split = DatasetSplit.TRAIN if is_train else DatasetSplit.VAL
        is_pro = True

        if self.model_type in ("jepa", "vl-jepa"):
            # B1.3: Val subsample stays fixed (GLOBAL_SEED) so early-stopping
            # comparisons are stable across epochs.  Only train rotates.
            seed = GLOBAL_SEED + epoch if is_train else GLOBAL_SEED
            sample_size = self._train_samples if is_train else self._val_samples
            raw_items = self.manager._fetch_jepa_ticks(
                is_pro=is_pro, split=split, seed=seed, sample_size=sample_size
            )
            if not raw_items:
                return []
            batches = []
            for i in range(0, len(raw_items), self.batch_size):
                batches.append(raw_items[i : i + self.batch_size])
            return batches
        else:
            rap_kwargs: dict = {"is_pro": is_pro, "split": split}
            if self.max_epochs <= 1:
                rap_kwargs["max_demos"] = 10
            windows = self.manager._fetch_rap_windows(**rap_kwargs)
            return windows if windows else []

    def _train_step_dispatch(self, trainer, tensor_batch, do_step):
        """Dispatch a single training step to the correct model-type path.

        Returns (loss: float, result: dict).
        """
        if self.model_type not in ("jepa", "vl-jepa"):
            result = trainer.train_step(tensor_batch, step_optimizer=do_step)
            if not isinstance(result, dict) or "loss" not in result:
                raise ValueError(
                    f"RAP train_step must return dict with 'loss' key, "
                    f"got {type(result).__name__}: "
                    f"{list(result.keys()) if isinstance(result, dict) else result}"
                )
            return float(result["loss"]), result

        if self._use_vl:
            result = trainer.train_step_vl(
                tensor_batch["context"],
                tensor_batch["target"],
                tensor_batch.get("negatives"),
                round_stats=tensor_batch.get("round_stats"),
                step_optimizer=do_step,
            )
            return float(result["total_loss"]), result

        result = trainer.train_step(
            tensor_batch["context"],
            tensor_batch["target"],
            tensor_batch.get("negatives"),
            step_optimizer=do_step,
        )
        loss = result["loss"] if isinstance(result, dict) else result
        if not isinstance(result, dict):
            result = {"loss": float(loss)}
        return float(loss), result

    def _eval_step_dispatch(self, trainer, tensor_batch):
        """Dispatch a single validation step (no grad). Returns loss float."""
        with torch.no_grad():
            if self.model_type in ("jepa", "vl-jepa"):
                return self._eval_step_jepa(trainer, tensor_batch)
            return self._eval_step_rap(trainer, tensor_batch)

    def _eval_step_jepa(self, trainer, tensor_batch):
        """JEPA/VL-JEPA validation: contrastive loss on pred vs target."""
        pred, target = trainer.model.forward_jepa_pretrain(
            tensor_batch["context"], tensor_batch["target"]
        )
        from Programma_CS2_RENAN.backend.nn.jepa_model import jepa_contrastive_loss

        # NN-H-02: Use shared encode_raw_negatives() for consistency
        # with training path (3D sequence expansion + mean pooling).
        raw_neg = tensor_batch.get("negatives")
        if raw_neg is not None:
            raw_neg = raw_neg.to(next(trainer.model.parameters()).device)
        seq_len = tensor_batch["context"].shape[1]
        neg_latent = trainer.encode_raw_negatives(raw_neg, seq_len)
        return jepa_contrastive_loss(pred, target, neg_latent).item()

    def _eval_step_rap(self, trainer, tensor_batch):
        """RAP validation: value estimate loss with optional val_mask."""
        outputs = trainer.model(
            tensor_batch["view"],
            tensor_batch["map"],
            tensor_batch["motion"],
            tensor_batch["metadata"],
            timespans=tensor_batch.get("timespans"),
        )
        val_mask = tensor_batch.get("val_mask")
        pred = outputs["value_estimate"]
        tgt = tensor_batch["target_val"]
        if val_mask is not None and not val_mask.any():
            return 0.0
        if val_mask is not None and val_mask.any() and not val_mask.all():
            return trainer.criterion_val(pred[val_mask], tgt[val_mask]).item()
        return trainer.criterion_val(pred, tgt).item()

    def _run_epoch(self, trainer, batches, is_train=True, context=None):
        """Run a single epoch (Train or Eval)."""
        total_loss = 0.0

        if is_train:
            trainer.model.train()
            if hasattr(trainer, "optimizer"):
                trainer.optimizer.zero_grad()
        else:
            trainer.model.eval()

        accum = self._accumulation_steps
        train_batch_count = 0

        for batch_idx, batch in enumerate(batches):
            if context:
                context.check_state()

            # P3-E: Drop undersized batches — BatchNorm fails with size 1
            if len(batch) < 2:
                logger.debug("P3-E: Dropping batch %d (size %d < 2)", batch_idx, len(batch))
                continue

            tensor_batch = self._prepare_tensor_batch(batch)
            if tensor_batch is None:
                continue

            if is_train:
                train_batch_count += 1
                do_step = train_batch_count % accum == 0
                loss, result = self._train_step_dispatch(trainer, tensor_batch, do_step)
                self.callbacks.fire(
                    "on_batch_end",
                    batch_idx=batch_idx,
                    loss=loss,
                    outputs=result,
                )
            else:
                loss = self._eval_step_dispatch(trainer, tensor_batch)

            total_loss += loss

        # Flush remaining accumulated gradients at end of epoch
        if is_train and train_batch_count % accum != 0:
            if hasattr(trainer, "_optimizer_step"):
                trainer._optimizer_step()

        return total_loss / max(len(batches), 1)

    def _prepare_tensor_batch(self, raw_items):
        """Convert list of DB objects (PlayerTickState) to Tensor Dictionary.

        Uses the unified FeatureExtractor to ensure consistency between training and inference.
        For RAP model: builds real Player-POV tensors from per-match databases when available,
        with graceful fallback to legacy zero-init when match DB is unavailable.
        """
        from Programma_CS2_RENAN.backend.processing.feature_engineering import FeatureExtractor

        b = len(raw_items)
        if b == 0:
            # CRITICAL: Never train on all-zero tensors — return None to signal skip
            logger.warning("Empty batch encountered — skipping (refusing to train on zeros)")
            return None

        # Extract features using the unified FeatureExtractor
        features = FeatureExtractor.extract_batch(raw_items)  # Shape: (b, METADATA_DIM)
        features_tensor = torch.tensor(features, dtype=torch.float32).to(self.device)

        if self.model_type in ("jepa", "vl-jepa"):
            # J-5 + V-1 FIX: Require context_len + 1 ticks minimum.
            # J-5: Zero vectors encode physically impossible game states.
            # V-1: With only context_len ticks, target = context[-1] (overlap —
            # model learns to "predict" what it already sees). With b >> context_len,
            # target was ticks[-1] (distant future, not next-step prediction).
            # Fix: target is the tick immediately AFTER the context window.
            _JEPA_CONTEXT_LEN = 10
            if b < _JEPA_CONTEXT_LEN + 1:
                logger.debug(
                    "V-1: JEPA batch too short (%d < %d) — need context + target tick",
                    b,
                    _JEPA_CONTEXT_LEN + 1,
                )
                return None

            # JEPA expects context (sequence), target, and negatives
            context = features_tensor[:_JEPA_CONTEXT_LEN].unsqueeze(0)  # (1, 10, METADATA_DIM)

            # V-1 FIX: Target is tick immediately after context — correct next-step prediction.
            # Previously used features_tensor[-1:] which overlapped with context when b=10
            # and was distant (89+ ticks away) when b>>10.
            target = features_tensor[_JEPA_CONTEXT_LEN : _JEPA_CONTEXT_LEN + 1].unsqueeze(
                0
            )  # (1, 1, METADATA_DIM)

            # NN-H-03: Sample negatives from cross-match pool (not current batch)
            # to avoid false negatives from same-match ticks.
            n_neg = self._n_contrastive_negatives
            if len(self._neg_pool) >= n_neg:
                if not self._neg_pool_ready_logged:
                    # W1.6 (NN-H-03): make the warmup→cross-match transition visible.
                    logger.info(
                        "NN-H-03: negative pool warmed up (%d features) — "
                        "switching from in-batch to cross-match negatives",
                        len(self._neg_pool),
                    )
                    self._neg_pool_ready_logged = True
                pool_tensor = torch.stack(self._neg_pool[-200:]).to(self.device)
                pool_idx = self._neg_rng.choice(len(pool_tensor), n_neg, replace=False)
                negatives = pool_tensor[pool_idx].unsqueeze(0)  # (1, 5, METADATA_DIM)
            elif b >= n_neg:
                # Pool warm-up: fall back to in-batch sampling until pool is populated
                neg_indices = self._neg_rng.choice(b, n_neg, replace=False)
                negatives = features_tensor[neg_indices].unsqueeze(0)
            else:
                logger.debug(
                    "JEPA batch too small for contrastive negatives (%d < %d) — skipping batch",
                    b,
                    n_neg,
                )
                return None

            # Populate pool with current batch features (after sampling to avoid self-negatives)
            step = max(1, b // 10)  # Store ~10 features per batch to limit pool growth
            for i in range(0, b, step):
                self._neg_pool.append(features_tensor[i].detach().cpu())
            if len(self._neg_pool) > self._neg_pool_max:
                self._neg_pool = self._neg_pool[-self._neg_pool_max :]

            result = {"context": context, "target": target, "negatives": negatives}

            # G-01: For VL-JEPA, fetch RoundStats to provide outcome-based concept labels
            # (eliminates label leakage from heuristic labeling)
            if self._use_vl:
                round_stats = self._fetch_round_stats_for_batch(raw_items[:_JEPA_CONTEXT_LEN])
                if round_stats is not None:
                    result["round_stats"] = round_stats

            return result
        else:
            return self._prepare_rap_batch(raw_items, features, features_tensor, b)

    # RAP-AUDIT-01: Temporal window size for LTC sequence processing.
    # Must match state_reconstructor.py default (32). Each window of
    # RAP_SEQ_LEN contiguous ticks becomes one batch sample with full
    # temporal context for the LTC ODE solver.
    RAP_SEQ_LEN = 32

    def _curriculum_seq_len(self) -> int:
        """Phase 5A: Ramp RAP window length during early epochs.

        Epochs 1-5 use progressively longer windows (8→32) to stabilize
        LTC ODE dynamics before exposing full temporal context.
        """
        full = self.RAP_SEQ_LEN
        if self._current_epoch > self._ltc_curriculum_epochs:
            return full
        frac = self._current_epoch / max(self._ltc_curriculum_epochs, 1)
        return max(8, int(full * (0.25 + 0.75 * frac)))

    def _prepare_rap_batch(self, raw_items, _features, features_tensor, b):
        """Build RAP tensor batch with temporal windows for LTC sequence processing.

        RAP-AUDIT-01: Segments input ticks into temporal windows of RAP_SEQ_LEN
        (32) ticks. Each window becomes one batch sample with seq_len=32, enabling
        the LTC to process actual temporal sequences with ODE dynamics across
        multiple timesteps — not single-tick snapshots.

        Phases (extracted as helpers below):
          Phase 1  (_rap_collect_per_tick)     resolves per-match DB, builds
                                               PlayerKnowledge, generates per-tick
                                               view/map/motion tensors, computes
                                               value+mask (LEAK-01 guard) and
                                               tactical role label per tick.
          Phase 2  (_rap_compute_target_pos)   per-tick position deltas (RAP-AUDIT-02).
          Phase 2b (_rap_compute_timespans)    inter-tick timespans (RAP-AUDIT-05).
          Phase 3  (_rap_segment_windows)      drop windows below min POV density.
          Phase 4  (this orchestrator)         stack windows into batch tensors.

        Returns the final batch dict, or None when no valid windows could form.
        """
        from Programma_CS2_RENAN.backend.nn.config import RAP_POSITION_SCALE
        from Programma_CS2_RENAN.backend.processing.player_knowledge import PlayerKnowledgeBuilder
        from Programma_CS2_RENAN.backend.processing.tensor_factory import (
            TensorFactory,
            TrainingTensorConfig,
        )

        tf = TensorFactory(TrainingTensorConfig())
        kb = PlayerKnowledgeBuilder()
        match_mgr = self._get_match_manager()
        caches = {"all_players": {}, "window": {}, "event": {}, "metadata": {}}

        per_tick = self._rap_collect_per_tick(raw_items, tf, kb, match_mgr, caches)
        per_tick["target_pos"] = self._rap_compute_target_pos(raw_items, RAP_POSITION_SCALE)
        per_tick["dt"] = self._rap_compute_timespans(
            raw_items, tick_rates=per_tick.get("tick_rates")
        )

        seq_len = self._curriculum_seq_len()
        num_windows = b // seq_len
        if num_windows == 0:
            logger.warning(
                "RAP batch has %d ticks < seq_len=%d — cannot form temporal window",
                b,
                seq_len,
            )
            return None

        windows = self._rap_segment_windows(per_tick, features_tensor, seq_len, num_windows)
        if windows is None:
            logger.warning("All RAP temporal windows lack POV data. Skipping batch.")
            return None

        n_valid = len(windows["views"])
        skipped = num_windows - n_valid
        self._total_samples += num_windows
        self._total_fallbacks += skipped
        if skipped > 0:
            fallback_rate = self._total_fallbacks / max(self._total_samples, 1) * 100
            logger.warning(
                "RAP batch: %d/%d temporal windows with POV data — %d skipped. "
                "Aggregate fallback rate: %.1f%%",
                n_valid,
                num_windows,
                skipped,
                fallback_rate,
            )
        else:
            logger.debug(
                "RAP batch: %d temporal windows (seq_len=%d) with POV data",
                n_valid,
                seq_len,
            )

        # 5D visual tensors: (B, T, C, H, W) — enables per-timestep perception
        view = torch.stack(windows["views"]).to(self.device)
        map_tensor = torch.stack(windows["maps"]).to(self.device)
        motion_tensor = torch.stack(windows["motions"]).to(self.device)
        # Metadata: (B, T, 25) — full temporal sequence for LTC
        metadata = torch.stack(windows["metadata"]).to(self.device)
        target_val = (
            torch.tensor(windows["target_val"], dtype=torch.float32).unsqueeze(1).to(self.device)
        )
        target_strat = torch.stack(windows["target_strat"]).to(self.device)
        val_mask = torch.tensor(windows["val_mask"], dtype=torch.bool).to(self.device)
        target_pos = torch.tensor(windows["target_pos"], dtype=torch.float32).to(self.device)
        timespans = torch.stack(windows["timespans"]).to(self.device)  # (B, T)

        return {
            "view": view,  # (B, T, C, H, W) — 5D for per-timestep perception
            "map": map_tensor,  # (B, T, C, H, W)
            "motion": motion_tensor,  # (B, T, C, H, W)
            "metadata": metadata,  # (B, T, 25) — temporal sequence, NOT unsqueeze(1)
            "target_strat": target_strat,  # (B, 10)
            "target_val": target_val,  # (B, 1)
            "val_mask": val_mask,  # (B,) NN-M-12: True = valid outcome
            "target_pos": target_pos,  # (B, 3) RAP-AUDIT-02: enables position head training
            "timespans": timespans,  # (B, T) RAP-AUDIT-05: inter-tick time intervals
        }

    def _rap_prefetch_caches(self, raw_items, match_mgr, caches):
        """Bulk pre-fetch match data for entire window: 2 queries instead of 288.

        Without this, _build_sample_knowledge issues 3 queries per tick with
        unique cache keys — zero reuse despite 99.7% data overlap between
        consecutive ticks (320-tick lookback shifts by 1 each tick).
        """
        if match_mgr is None:
            return

        match_tick_map: dict = {}
        for item in raw_items:
            mid = getattr(item, "match_id", None)
            if mid is None:
                demo_name = str(getattr(item, "demo_name", "") or "")
                if demo_name:
                    from Programma_CS2_RENAN.backend.storage.match_data_manager import (
                        demo_name_to_match_id,
                    )

                    mid = demo_name_to_match_id(demo_name)
            if mid is not None:
                match_tick_map.setdefault(mid, []).append(int(getattr(item, "tick", 0)))

        if not match_tick_map:
            return

        all_players_cache = caches["all_players"]
        window_cache = caches["window"]
        event_cache = caches["event"]

        for match_id, ticks in match_tick_map.items():
            min_tick = min(ticks)
            max_tick = max(ticks)
            lookback_start = max(0, min_tick - 320)
            event_end = max_tick + 64

            try:
                bulk_states = match_mgr.get_all_players_tick_window(
                    match_id, max_tick, window_size=max_tick - lookback_start
                )

                for t in ticks:
                    ap_key = (match_id, t)
                    if ap_key not in all_players_cache:
                        all_players_cache[ap_key] = bulk_states.get(t, [])

                for t in ticks:
                    wnd_key = (match_id, t)
                    if wnd_key not in window_cache:
                        wnd_start = max(0, t - 320)
                        window_cache[wnd_key] = {
                            k: v for k, v in bulk_states.items() if wnd_start <= k <= t
                        }

                bulk_events = match_mgr.get_events_for_tick_range(
                    match_id, lookback_start, event_end
                )

                for t in ticks:
                    evt_key = (match_id, t)
                    if evt_key not in event_cache:
                        evt_start = max(0, t - 320)
                        evt_end_t = t + 64
                        event_cache[evt_key] = [
                            e for e in bulk_events if evt_start <= e.tick <= evt_end_t
                        ]

            except Exception as e:
                logger.debug("Bulk prefetch failed for match_id=%s: %s", match_id, e)

    def _rap_collect_per_tick(self, raw_items, tf, kb, match_mgr, caches):
        """Phase 1: per-tick tensors, value+mask (LEAK-01), strat label.

        Returns a dict with the per_tick_* lists keyed as views/maps/motions/
        has_pov/vals/val_masks/strats. The LEAK-01 guard remains intact: when
        we lack a knowledge object or the all_players context for a tick, the
        value defaults to 0.0 with mask=False so the sample is excluded from
        the value-head loss instead of being trained on the future-leaked
        round_outcome label.
        """
        self._rap_prefetch_caches(raw_items, match_mgr, caches)
        per_tick_view: list = []
        per_tick_map: list = []
        per_tick_motion: list = []
        per_tick_has_pov: list = []
        per_tick_val: list = []
        per_tick_val_mask: list = []
        per_tick_strat: list = []
        per_tick_tick_rate: list = []
        pov_count = 0

        all_players_cache = caches["all_players"]
        metadata_cache = caches["metadata"]
        window_cache = caches["window"]
        event_cache = caches["event"]

        # C1.2 (26-TICK-01): one PlayerKnowledgeBuilder per distinct server tick rate
        # (seeded with the rate-64 builder passed in) so 128-tick demos get correct
        # real-time memory/flash windows. Imported lazily to mirror _build_rap_batch.
        from Programma_CS2_RENAN.backend.processing.player_knowledge import PlayerKnowledgeBuilder

        kb_by_rate = {getattr(kb, "tick_rate", 64): kb}

        for i, item in enumerate(raw_items):
            match_id = getattr(item, "match_id", None)
            tick = int(getattr(item, "tick", 0))
            player_name = str(getattr(item, "player_name", ""))
            demo_name = str(getattr(item, "demo_name", "") or "")

            # POV-RAP-FIX-2 (Sprint A 2026-04-26): PlayerTickState rows in the
            # monolith have match_id=None but demo_name set; per-match shards
            # are keyed by the SHA-256-derived numeric ID. Without this fall-
            # back the POV gate dropped every batch (commit b091f83 = tablename
            # half; this is the FK half).
            if match_id is None and demo_name:
                from Programma_CS2_RENAN.backend.storage.match_data_manager import (
                    demo_name_to_match_id,
                )

                match_id = demo_name_to_match_id(demo_name)

            map_name = self._resolve_map_name(match_id, demo_name, match_mgr, metadata_cache)

            # C1.2: per-demo tick rate selects the matching knowledge builder.
            tick_rate = self._resolve_tick_rate(match_id, match_mgr, metadata_cache)
            per_tick_tick_rate.append(tick_rate)
            kb_item = kb_by_rate.get(tick_rate)
            if kb_item is None:
                kb_item = PlayerKnowledgeBuilder(tick_rate=tick_rate)
                kb_by_rate[tick_rate] = kb_item

            knowledge = None
            tick_list = [item]

            if match_id is not None and match_mgr is not None:
                try:
                    knowledge, tick_list = self._build_sample_knowledge(
                        match_id,
                        tick,
                        player_name,
                        item,
                        match_mgr,
                        kb_item,
                        all_players_cache,
                        window_cache,
                        event_cache,
                    )
                    if knowledge is not None:
                        pov_count += 1
                except Exception as e:
                    logger.debug(
                        "Match DB unavailable for match_id=%s tick=%s: %s",
                        match_id,
                        tick,
                        e,
                    )

            per_tick_has_pov.append(knowledge is not None)

            # Generate tensors (real POV or legacy zero-fallback)
            map_t = tf.generate_map_tensor(tick_list, map_name, knowledge=knowledge)
            view_t = tf.generate_view_tensor(tick_list, map_name, knowledge=knowledge)
            motion_t = tf.generate_motion_tensor(tick_list, map_name)

            per_tick_map.append(map_t)
            per_tick_view.append(view_t)
            per_tick_motion.append(motion_t)

            # Advantage function (continuous [0, 1])
            all_players = all_players_cache.get((match_id, tick), [])
            if all_players and knowledge is not None:
                val = self._compute_advantage(
                    all_players,
                    str(getattr(item, "team", "CT")),
                    knowledge.bomb_planted,
                )
                per_tick_val_mask.append(True)
            else:
                # LEAK-01 fix: round_outcome is the final round result (known only
                # at round end). Using it as the per-tick value target leaks future
                # information into the value head. Mask the sample instead of
                # substituting the leaky label.
                val = 0.0
                per_tick_val_mask.append(False)
            per_tick_val.append(val)

            # Tactical role label (10 classes)
            strat_idx = self._classify_tactical_role(item, knowledge, all_players)
            strat_vec = torch.zeros(10)
            strat_vec[strat_idx] = 1.0
            per_tick_strat.append(strat_vec)

        return {
            "views": per_tick_view,
            "maps": per_tick_map,
            "motions": per_tick_motion,
            "has_pov": per_tick_has_pov,
            "vals": per_tick_val,
            "val_masks": per_tick_val_mask,
            "strats": per_tick_strat,
            "tick_rates": per_tick_tick_rate,
            "pov_count": pov_count,
        }

    @staticmethod
    def _rap_compute_target_pos(raw_items, position_scale):
        """RAP-AUDIT-02: per-tick self-supervised next-position deltas.

        Without this, the position head sees zero loss every step and never
        trains. Last tick gets [0,0,0] (no successor available).
        """
        per_tick_target_pos: list = []
        for i in range(len(raw_items)):
            if i + 1 < len(raw_items):
                cur = raw_items[i]
                nxt = raw_items[i + 1]
                dx = (getattr(nxt, "pos_x", 0) - getattr(cur, "pos_x", 0)) / position_scale
                dy = (getattr(nxt, "pos_y", 0) - getattr(cur, "pos_y", 0)) / position_scale
                dz = (getattr(nxt, "pos_z", 0) - getattr(cur, "pos_z", 0)) / position_scale
                per_tick_target_pos.append([dx, dy, dz])
            else:
                per_tick_target_pos.append([0.0, 0.0, 0.0])
        return per_tick_target_pos

    @staticmethod
    def _rap_compute_timespans(raw_items, default_tick_rate: float = 64.0, tick_rates=None):
        """RAP-AUDIT-05 / C1.2 (26-TICK-03): inter-tick timespans for the LTC ODE solver.

        Without real timespans the LTC treats every tick as 1.0s and loses its
        continuous-time advantage over LSTM. The elapsed seconds between ticks is
        ``(nxt_tick - cur_tick) / tick_rate``; on a 128-tick demo the rate is 128, so a
        fixed 64 would feed the LTC a 2x-too-large dt. ``tick_rates`` (per-item, from
        ``MatchMetadata`` via ``_resolve_tick_rate``) overrides ``default_tick_rate`` so
        each demo's real server rate is used; it falls back to the default when absent.
        """
        per_tick_dt: list = []
        n = len(raw_items)
        for i in range(n):
            rate = default_tick_rate
            if tick_rates is not None and i < len(tick_rates) and tick_rates[i]:
                rate = float(tick_rates[i])
            if i + 1 < n:
                cur_tick = int(getattr(raw_items[i], "tick", 0))
                nxt_tick = int(getattr(raw_items[i + 1], "tick", 0))
                dt = max((nxt_tick - cur_tick) / rate, 1e-4)
            else:
                dt = per_tick_dt[-1] if per_tick_dt else 1.0 / rate
            per_tick_dt.append(dt)
        return per_tick_dt

    @staticmethod
    def _resolve_tick_rate(match_id, match_mgr, metadata_cache, default: int = 64) -> int:
        """C1.2 (26-TICK-01/03): per-demo server tick rate from cached MatchMetadata.

        Reuses the same ``metadata_cache`` populated by ``_resolve_map_name`` so no
        extra DB round-trips occur. Falls back to ``default`` (64) when metadata is
        missing, and rejects out-of-range values (valid window [32, 256], per DS-07).
        """
        try:
            if match_id not in metadata_cache and match_mgr is not None:
                try:
                    metadata_cache[match_id] = match_mgr.get_metadata(match_id)
                except Exception:
                    # 26-ORCH-02: mirror analysis_orchestrator._resolve_tick_rate —
                    # every fallback branch warns; nothing falls back silently.
                    logger.warning(
                        "26-ORCH-02: MatchMetadata lookup failed for match %s — "
                        "tick rate will fall back to %d",
                        match_id,
                        default,
                        exc_info=True,
                    )
                    metadata_cache[match_id] = None
            meta = metadata_cache.get(match_id)
            if meta is not None:
                rate = int(getattr(meta, "tick_rate", default) or default)
                if 32 <= rate <= 256:
                    return rate
        except Exception:
            # 26-ORCH-02: same rule for the outer guard.
            logger.warning(
                "26-ORCH-02: tick-rate resolution failed for match %s — " "falling back to %d",
                match_id,
                default,
                exc_info=True,
            )
        return default

    @staticmethod
    def _rap_segment_windows(per_tick, features_tensor, seq_len: int, num_windows: int):
        """Phase 3: split per-tick lists into RAP_SEQ_LEN windows; drop sparse-POV ones.

        T-2 FIX: requires ≥50% POV density per window. Previously only dropped
        windows with ZERO POV (1/32 = 3.1% kept), so windows dominated by zero-
        init fallback tensors taught the model that vision data is uninformative.

        Returns dict of window_* lists, or None if every window was dropped.
        """
        _MIN_POV_DENSITY = 0.5

        window_views: list = []
        window_maps: list = []
        window_motions: list = []
        window_metadata: list = []
        window_target_val: list = []
        window_target_strat: list = []
        window_val_mask: list = []
        window_target_pos: list = []
        window_timespans: list = []

        for w in range(num_windows):
            start = w * seq_len
            end = start + seq_len

            window_pov_count = sum(1 for ok in per_tick["has_pov"][start:end] if ok)
            if window_pov_count / seq_len < _MIN_POV_DENSITY:
                continue

            window_views.append(torch.stack(per_tick["views"][start:end]))
            window_maps.append(torch.stack(per_tick["maps"][start:end]))
            window_motions.append(torch.stack(per_tick["motions"][start:end]))
            window_metadata.append(features_tensor[start:end])
            window_timespans.append(torch.tensor(per_tick["dt"][start:end], dtype=torch.float32))

            last_idx = end - 1
            window_target_val.append(per_tick["vals"][last_idx])
            window_target_strat.append(per_tick["strats"][last_idx])
            window_val_mask.append(per_tick["val_masks"][last_idx])
            window_target_pos.append(per_tick["target_pos"][last_idx])

        if not window_views:
            return None

        return {
            "views": window_views,
            "maps": window_maps,
            "motions": window_motions,
            "metadata": window_metadata,
            "target_val": window_target_val,
            "target_strat": window_target_strat,
            "val_mask": window_val_mask,
            "target_pos": window_target_pos,
            "timespans": window_timespans,
        }

    def _build_sample_knowledge(
        self,
        match_id,
        tick,
        player_name,
        item,
        match_mgr,
        kb,
        all_players_cache,
        window_cache,
        event_cache,
    ):
        """Build PlayerKnowledge for a single training sample.

        Returns (knowledge, tick_list) or (None, [item]) on failure.
        Uses per-batch caches to avoid redundant queries.
        """
        # All players at this tick
        ap_key = (match_id, tick)
        if ap_key not in all_players_cache:
            all_players_cache[ap_key] = match_mgr.get_all_players_at_tick(match_id, tick)
        all_players = all_players_cache[ap_key]

        if not all_players:
            return None, [item]

        # Find our player in per-match data
        our_player_tick = None
        for p in all_players:
            if str(getattr(p, "player_name", "")) == player_name:
                our_player_tick = p
                break

        if our_player_tick is None:
            return None, [item]

        # Recent history for enemy memory (320-tick window)
        wnd_key = (match_id, tick)
        if wnd_key not in window_cache:
            window_cache[wnd_key] = match_mgr.get_all_players_tick_window(
                match_id, tick, window_size=320
            )
        recent_history = window_cache[wnd_key]

        # Events for sound + utility
        evt_key = (match_id, tick)
        if evt_key not in event_cache:
            event_cache[evt_key] = match_mgr.get_events_for_tick_range(
                match_id, max(0, tick - 320), tick + 64
            )
        events = event_cache[evt_key]

        knowledge = kb.build_knowledge(
            our_player_tick,
            all_players,
            recent_all_players_history=recent_history,
            active_events=events,
        )

        return knowledge, [our_player_tick]

    def _get_match_manager(self):
        """Get the match data manager singleton, or None if unavailable."""
        try:
            from Programma_CS2_RENAN.backend.storage.match_data_manager import (
                get_match_data_manager,
            )

            return get_match_data_manager()
        except Exception as e:
            logger.debug("Match data manager unavailable: %s", e)
            return None

    @staticmethod
    def _resolve_map_name(match_id, demo_name, match_mgr, metadata_cache):
        """Resolve map name from match metadata or demo_name pattern.

        Priority: match metadata DB > regex on demo_name > fallback "de_mirage".
        """
        # Try match metadata first
        if match_id is not None and match_mgr is not None:
            if match_id not in metadata_cache:
                try:
                    metadata_cache[match_id] = match_mgr.get_metadata(match_id)
                except Exception:
                    logger.debug("Metadata cache miss for match_id=%s", match_id, exc_info=True)
                    metadata_cache[match_id] = None

            meta = metadata_cache.get(match_id)
            if meta is not None and getattr(meta, "map_name", ""):
                return (
                    "de_" + meta.map_name if not meta.map_name.startswith("de_") else meta.map_name
                )

        # Fallback: extract from demo_name
        known_maps = (
            "mirage",
            "inferno",
            "dust2",
            "ancient",
            "nuke",
            "anubis",
            "overpass",
            "vertigo",
        )
        demo_lower = demo_name.lower()
        for m in known_maps:
            if m in demo_lower:
                return f"de_{m}"

        logger.warning(
            "C-1: map fallback to de_mirage — no metadata and demo_name=%r "
            "matched no known map. Spatial tensors may be wrong for this window.",
            demo_name,
        )
        return "de_mirage"

    # ============ G-01: RoundStats Fetch for VL-JEPA ============

    def _fetch_round_stats_for_batch(self, raw_items):
        """Fetch RoundStats for batch items to provide outcome-based concept labels.

        Returns a list of RoundStats objects (one per item, None if unavailable),
        or None if no RoundStats could be found at all.
        """
        try:
            from sqlmodel import select

            from Programma_CS2_RENAN.backend.storage.database import get_db_manager
            from Programma_CS2_RENAN.backend.storage.db_models import RoundStats

            db = get_db_manager()

            # Collect unique (demo_name, player_name) pairs
            demo_player_pairs = set()
            for item in raw_items:
                demo = getattr(item, "demo_name", None)
                player = getattr(item, "player_name", None)
                if demo and player:
                    demo_player_pairs.add((demo, player))

            if not demo_player_pairs:
                return None

            # Fetch all relevant RoundStats in one query
            with db.get_session() as session:
                stats_by_key = {}
                for demo, player in demo_player_pairs:
                    rows = session.exec(
                        select(RoundStats)
                        .where(RoundStats.demo_name == demo, RoundStats.player_name == player)
                        .limit(50)
                    ).all()
                    for rs in rows:
                        stats_by_key[(demo, player, rs.round_number)] = rs

            if not stats_by_key:
                return None

            # Map each batch item to its RoundStats (use round_number estimate from tick)
            result = []
            found = 0
            for item in raw_items:
                demo = getattr(item, "demo_name", None)
                player = getattr(item, "player_name", None)
                tick = getattr(item, "tick", 0)
                # Estimate round number from tick (64 tick/s, ~115s per round)
                est_round = max(1, tick // (64 * 115) + 1)

                rs = None
                if demo and player:
                    # Try exact round, then nearest
                    rs = stats_by_key.get((demo, player, est_round))
                    if rs is None:
                        # Try round 1 as fallback (common for early ticks)
                        rs = stats_by_key.get((demo, player, 1))

                result.append(rs)
                if rs is not None:
                    found += 1

            if found == 0:
                return None

            return result

        except Exception as e:
            logger.debug("RoundStats fetch for VL-JEPA failed (non-fatal): %s", e)
            return None

    # ============ Training Target Computation ============

    # Advantage function weights
    _ADV_W_ALIVE = 0.4
    _ADV_W_HP = 0.2
    _ADV_W_EQUIP = 0.2
    _ADV_W_BOMB = 0.2

    # Tactical role thresholds
    _SAVE_EQUIP_THRESHOLD = 1500
    _LURK_DISTANCE_THRESHOLD = 1500.0
    _ENTRY_DISTANCE_THRESHOLD = 800.0
    _SUPPORT_DISTANCE_THRESHOLD = 500.0

    # Tactical role indices
    ROLE_SITE_TAKE = 0
    ROLE_ROTATION = 1
    ROLE_ENTRY_FRAG = 2
    ROLE_SUPPORT = 3
    ROLE_ANCHOR = 4
    ROLE_LURK = 5
    ROLE_RETAKE = 6
    ROLE_SAVE = 7
    ROLE_AGGRESSIVE_PUSH = 8
    ROLE_PASSIVE_HOLD = 9

    @staticmethod
    def _compute_advantage(all_players_at_tick, player_team, bomb_planted):
        """Compute continuous advantage value [0, 1] from game state.

        Formula: 0.4 * alive_diff + 0.2 * hp_ratio + 0.2 * equip_ratio + 0.2 * bomb_factor

        This replaces binary win/lose (G-04) with a granular signal that
        reflects the actual tactical advantage at each tick.
        """
        team_alive = 0
        team_hp = 0
        team_equip = 0
        enemy_alive = 0
        enemy_hp = 0
        enemy_equip = 0

        for p in all_players_at_tick:
            if not getattr(p, "is_alive", True):
                continue
            p_team = str(getattr(p, "team", ""))
            hp = int(getattr(p, "health", 100))
            equip = int(getattr(p, "equipment_value", 0))

            if p_team == player_team:
                team_alive += 1
                team_hp += hp
                team_equip += equip
            else:
                enemy_alive += 1
                enemy_hp += hp
                enemy_equip += equip

        # alive_diff: normalize [-5, 5] → [0, 1]
        alive_diff = (team_alive - enemy_alive + 5) / 10.0
        alive_diff = max(0.0, min(1.0, alive_diff))

        # HP ratio: team HP / total HP
        total_hp = team_hp + enemy_hp
        hp_ratio = team_hp / total_hp if total_hp > 0 else 0.5

        # Equipment ratio: team equip / total equip
        total_equip = team_equip + enemy_equip
        equip_ratio = team_equip / total_equip if total_equip > 0 else 0.5

        # Bomb factor: planted → advantage for T, disadvantage for CT
        bomb_factor = 0.5
        if bomb_planted:
            bomb_factor = 0.7 if player_team == "T" else 0.3

        advantage = (
            TrainingOrchestrator._ADV_W_ALIVE * alive_diff
            + TrainingOrchestrator._ADV_W_HP * hp_ratio
            + TrainingOrchestrator._ADV_W_EQUIP * equip_ratio
            + TrainingOrchestrator._ADV_W_BOMB * bomb_factor
        )
        return max(0.0, min(1.0, advantage))

    def _classify_tactical_role(self, item, knowledge, all_players):
        """Classify tactical role from game state heuristics.

        Returns index 0-9 for one of:
        site_take, rotation, entry_frag, support, anchor,
        lurk, retake, save, aggressive_push, passive_hold

        When PlayerKnowledge is available, uses teammate distances, enemy
        visibility, and bomb state for classification. Falls back to
        simplified team-based default when knowledge is unavailable.
        """
        team = str(getattr(item, "team", "CT"))
        is_ct = team == "CT"
        equip = int(getattr(item, "equipment_value", 0) or 0)
        is_crouching = bool(getattr(item, "is_crouching", False))

        # Save round detection (lowest priority override — equipment too low)
        if equip < self._SAVE_EQUIP_THRESHOLD:
            return self.ROLE_SAVE

        # Without knowledge, use simple team-based defaults
        if knowledge is None:
            return self.ROLE_PASSIVE_HOLD if is_ct else self.ROLE_SITE_TAKE

        # --- Knowledge-informed classification ---
        bomb_planted = knowledge.bomb_planted
        has_visible_enemies = knowledge.visible_enemy_count > 0
        teammates = knowledge.teammate_positions

        avg_team_dist = 0.0
        if teammates:
            avg_team_dist = sum(tm.distance for tm in teammates) / len(teammates)

        # CT + bomb planted → retake
        if is_ct and bomb_planted:
            return self.ROLE_RETAKE

        # Lurk (far from team, no visible enemies)
        if avg_team_dist > self._LURK_DISTANCE_THRESHOLD and not has_visible_enemies:
            return self.ROLE_LURK

        # Entry frag (visible enemies + close range)
        if has_visible_enemies and knowledge.visible_enemies:
            closest_dist = min(e.distance for e in knowledge.visible_enemies)
            if closest_dist < self._ENTRY_DISTANCE_THRESHOLD:
                return self.ROLE_ENTRY_FRAG
            # Visible enemies but farther → aggressive push
            return self.ROLE_AGGRESSIVE_PUSH

        # CT-specific roles
        if is_ct:
            if is_crouching:
                return self.ROLE_ANCHOR
            return self.ROLE_PASSIVE_HOLD

        # T-specific roles
        if avg_team_dist < self._SUPPORT_DISTANCE_THRESHOLD and len(teammates) >= 2:
            return self.ROLE_SUPPORT

        return self.ROLE_SITE_TAKE

    def _report_progress(self, epoch, t_loss, v_loss):
        """Update Dashboard State."""
        msg = f"Epoch {epoch}/{self.max_epochs} | Train: {t_loss:.4f} | Val: {v_loss:.4f}"
        logger.info(msg)
        self.manager._update_state("Training", msg)
