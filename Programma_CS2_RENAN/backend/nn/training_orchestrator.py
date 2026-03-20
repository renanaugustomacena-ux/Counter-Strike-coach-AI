import numpy as np
import torch

from Programma_CS2_RENAN.backend.nn.config import get_device
from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError, load_nn, save_nn
from Programma_CS2_RENAN.backend.nn.training_callbacks import CallbackRegistry
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.orchestrator")


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

    def __init__(
        self,
        manager,
        model_type="jepa",
        max_epochs=100,
        patience=10,
        batch_size=32,
        callbacks: CallbackRegistry = None,
    ):
        self.manager = manager
        self.model_type = model_type
        self.max_epochs = max_epochs
        self.patience = patience
        self.batch_size = batch_size
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
        # F3-11: Aggregate zero-tensor fallback counters across entire training run
        self._total_samples = 0
        self._total_fallbacks = 0

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

    def run_training(self, context=None):
        """Execute the full training pipeline."""
        logger.info("Orchestrator Starting: %s Cycle", self.model_name.upper())

        # GPU detection — warn early so user knows training will be slow
        if not torch.cuda.is_available():
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
                pass  # Non-fatal — don't block training over a notification

        # P3-D: Pre-training data quality gate
        from Programma_CS2_RENAN.backend.nn.data_quality import run_pre_training_quality_check

        quality_report = run_pre_training_quality_check()
        if not quality_report.passed:
            logger.error(
                "P3-D: Training ABORTED — pre-training quality check FAILED.\n%s",
                quality_report.summary(),
            )
            return

        # 1. Initialize Model via Factory
        # This unifies instantiation logic with Inference Engine
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        # Mapping generic orchestrator type to Factory constants if needed,
        # but they seem to match ("jepa", "rap").
        # If model_type is 'rap', we assume it's ModelFactory.TYPE_RAP.

        model = ModelFactory.get_model(self.model_type).to(self.device)
        try:
            # Try loading existing checkpoint to resume
            load_nn(self.model_name, model)
            logger.info("Resumed training from %s", self.model_name)
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

        trainer_kwargs = {"lr": self.learning_rate}
        if self.model_type in ("jepa", "vl-jepa"):
            trainer_kwargs["t_max"] = self.max_epochs  # NN-M-10: sync scheduler with epochs
        trainer = self.TrainerClass(model, **trainer_kwargs)

        # 2. Prepare Data
        # Phase 5.2 Alignment: Using standardized fetching with splits
        train_data = self._fetch_batches(is_train=True)
        val_data = self._fetch_batches(is_train=False)

        if not train_data:
            logger.warning("Training Aborted: Insufficient Training Data")
            return

        # P3-C: Minimum sample threshold — refuse to train on tiny datasets
        total_train_samples = len(train_data) * self.batch_size
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
            "Training on %s samples, Validating on %s",
            total_train_samples,
            len(val_data) * self.batch_size if val_data else 0,
        )

        # Fire: on_train_start
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

        # 3. Epoch Loop
        for epoch in range(1, self.max_epochs + 1):
            if context:
                context.check_state()

            # Fire: on_epoch_start
            self.callbacks.fire("on_epoch_start", epoch=epoch)

            # A. Train
            train_loss = self._run_epoch(trainer, train_data, is_train=True, context=context)

            # B. Validate
            val_loss = 0.0
            if val_data:
                val_loss = self._run_epoch(trainer, val_data, is_train=False, context=context)
            else:
                val_loss = train_loss  # Fallback if no val data

            # C. Scheduler Step (if trainer has one)
            if hasattr(trainer, "scheduler") and trainer.scheduler is not None:
                trainer.scheduler.step()

            # D. Logging & Reporting
            self._report_progress(epoch, train_loss, val_loss)

            # Fire: on_epoch_end
            self.callbacks.fire(
                "on_epoch_end",
                epoch=epoch,
                train_loss=train_loss,
                val_loss=val_loss,
                model=model,
                optimizer=trainer.optimizer if hasattr(trainer, "optimizer") else None,
            )

            # E. Checkpointing & Early Stopping
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.patience_counter = 0
                save_nn(model, self.model_name, user_id=None)  # Save BEST
                logger.info("New Best Model Saved (Val Loss: %s)", format(val_loss, ".6f"))
            else:
                self.patience_counter += 1

            # Save LATEST checkpoint regardless
            save_nn(model, f"{self.model_name}_latest", user_id=None)

            if self.patience_counter >= self.patience:
                logger.info("Early Stopping Triggered at Epoch %s", epoch)
                break

        # P3-C: Hard gate — abort if aggregate fallback rate exceeds 30%
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

        # Fire: on_train_end
        self.callbacks.fire(
            "on_train_end",
            model=model,
            final_metrics={
                "best_val_loss": self.best_val_loss,
                "final_epoch": epoch,
                "model_type": self.model_type,
                "fallback_rate": (
                    self._total_fallbacks / max(self._total_samples, 1)
                    if self._total_samples > 0
                    else 0.0
                ),
            },
        )

        logger.info("Training Cycle Complete.")

    def _fetch_batches(self, is_train=True):
        """Fetch and batch data from Manager."""
        split = "train" if is_train else "val"
        is_pro = True  # Start with Pro baseline by default

        if self.model_type in ("jepa", "vl-jepa"):
            raw_items = self.manager._fetch_jepa_ticks(is_pro=is_pro, split=split)
            if not raw_items:
                return []
            # Temporal ordering preserved — no shuffle for sequence models
            batches = []
            for i in range(0, len(raw_items), self.batch_size):
                batches.append(raw_items[i : i + self.batch_size])
            return batches
        else:
            # P7: RAP uses windowed data — each window is a contiguous
            # 320-tick segment from a single match, already a batch.
            windows = self.manager._fetch_rap_windows(is_pro=is_pro, split=split)
            return windows if windows else []

    def _run_epoch(self, trainer, batches, is_train=True, context=None):
        """Run a single epoch (Train or Eval)."""
        total_loss = 0.0

        if is_train:
            trainer.model.train()
        else:
            trainer.model.eval()

        for batch_idx, batch in enumerate(batches):
            if context:
                context.check_state()

            # P3-E: Drop undersized batches — BatchNorm fails with size 1
            if len(batch) < 2:
                logger.debug("P3-E: Dropping batch %d (size %d < 2)", batch_idx, len(batch))
                continue

            # Convert raw DB objects to Tensors
            tensor_batch = self._prepare_tensor_batch(batch)
            if tensor_batch is None:
                continue  # Skip empty batches

            if is_train:
                # Trainer handles zero_grad, backward, optimizer
                if self.model_type in ("jepa", "vl-jepa"):
                    # JEPA signature: context, target, negatives
                    if self._use_vl:
                        result = trainer.train_step_vl(
                            tensor_batch["context"],
                            tensor_batch["target"],
                            tensor_batch.get("negatives"),
                            round_stats=tensor_batch.get("round_stats"),
                        )
                        loss = result["total_loss"]
                    else:
                        result = trainer.train_step(
                            tensor_batch["context"],
                            tensor_batch["target"],
                            tensor_batch.get("negatives"),
                        )
                        loss = result["loss"] if isinstance(result, dict) else result
                else:
                    # RAP signature: batch dict directly — returns dict with "loss" key.
                    # KeyError here is a programming bug (not data) — let it propagate.
                    result = trainer.train_step(tensor_batch)
                    if not isinstance(result, dict) or "loss" not in result:
                        raise ValueError(
                            f"RAP train_step must return dict with 'loss' key, "
                            f"got {type(result).__name__}: "
                            f"{list(result.keys()) if isinstance(result, dict) else result}"
                        )
                    loss = result["loss"]

                # Fire: on_batch_end (training batches only)
                batch_outputs = result if isinstance(result, dict) else {"loss": float(loss)}
                self.callbacks.fire(
                    "on_batch_end",
                    batch_idx=batch_idx,
                    loss=float(loss),
                    outputs=batch_outputs,
                )
            else:
                # Validation (No Grad)
                with torch.no_grad():
                    if self.model_type in ("jepa", "vl-jepa"):
                        # For validation, just compute loss without backward
                        pred, target = trainer.model.forward_jepa_pretrain(
                            tensor_batch["context"], tensor_batch["target"]
                        )
                        from Programma_CS2_RENAN.backend.nn.jepa_model import jepa_contrastive_loss

                        # NN-H-02: Use shared encode_raw_negatives() for consistency
                        # with training path (3D sequence expansion + mean pooling).
                        raw_neg = tensor_batch.get("negatives")
                        seq_len = tensor_batch["context"].shape[1]
                        neg_latent = trainer.encode_raw_negatives(raw_neg, seq_len)

                        loss = jepa_contrastive_loss(pred, target, neg_latent).item()
                    else:
                        # RAP validation — KeyError = programming bug, let it propagate.
                        outputs = trainer.model(
                            tensor_batch["view"],
                            tensor_batch["map"],
                            tensor_batch["motion"],
                            tensor_batch["metadata"],
                        )
                        val_mask = tensor_batch.get("val_mask")
                        pred = outputs["value_estimate"]
                        tgt = tensor_batch["target_val"]
                        if val_mask is not None and val_mask.any() and not val_mask.all():
                            loss = trainer.criterion_val(pred[val_mask], tgt[val_mask]).item()
                        elif val_mask is not None and not val_mask.any():
                            loss = 0.0
                        else:
                            loss = trainer.criterion_val(pred, tgt).item()

            total_loss += loss

        return total_loss / max(len(batches), 1)

    def _prepare_tensor_batch(self, raw_items):
        """Convert list of DB objects (PlayerTickState) to Tensor Dictionary.

        Uses the unified FeatureExtractor to ensure consistency between training and inference.
        For RAP model: builds real Player-POV tensors from per-match databases when available,
        with graceful fallback to legacy zero-init when match DB is unavailable.
        """
        from Programma_CS2_RENAN.backend.processing.feature_engineering import (
            METADATA_DIM,
            FeatureExtractor,
        )

        b = len(raw_items)
        if b == 0:
            # CRITICAL: Never train on all-zero tensors — return None to signal skip
            logger.warning("Empty batch encountered — skipping (refusing to train on zeros)")
            return None

        # Extract features using the unified FeatureExtractor
        features = FeatureExtractor.extract_batch(raw_items)  # Shape: (b, METADATA_DIM)
        features_tensor = torch.tensor(features, dtype=torch.float32).to(self.device)

        if self.model_type in ("jepa", "vl-jepa"):
            # JEPA expects context (sequence), target, and negatives
            # Context: use sliding window of features
            context_len = min(10, b)
            context = features_tensor[:context_len].unsqueeze(0)  # (1, context_len, METADATA_DIM)
            # Pad to 10 if needed
            if context.shape[1] < 10:
                padding = torch.zeros(1, 10 - context.shape[1], METADATA_DIM).to(self.device)
                context = torch.cat([context, padding], dim=1)

            # Target: next item prediction — must be 3D (B, seq_len, input_dim)
            target = features_tensor[-1:].unsqueeze(0)  # (1, 1, METADATA_DIM)

            # NN-H-03: Sample negatives from cross-match pool (not current batch)
            # to avoid false negatives from same-match ticks.
            n_neg = 5
            if len(self._neg_pool) >= n_neg:
                pool_tensor = torch.stack(self._neg_pool[-200:])  # Up to 200 candidates
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
                round_stats = self._fetch_round_stats_for_batch(raw_items[:context_len])
                if round_stats is not None:
                    result["round_stats"] = round_stats

            return result
        else:
            return self._prepare_rap_batch(raw_items, features, features_tensor, b)

    def _prepare_rap_batch(self, raw_items, _features, features_tensor, b):
        """Build RAP tensor batch with real Player-POV tensors.

        For each sample, attempts to:
        1. Resolve the per-match DB from match_id
        2. Query all players at tick + recent history + events
        3. Build PlayerKnowledge (NO-WALLHACK sensorial model)
        4. Generate real map/view/motion tensors at 64x64 training resolution

        Falls back to legacy zero-init per-sample when match DB is unavailable.
        """
        from Programma_CS2_RENAN.backend.processing.player_knowledge import PlayerKnowledgeBuilder
        from Programma_CS2_RENAN.backend.processing.tensor_factory import (
            TensorFactory,
            TrainingTensorConfig,
        )

        tf = TensorFactory(TrainingTensorConfig())
        kb = PlayerKnowledgeBuilder()
        match_mgr = self._get_match_manager()

        metadata = features_tensor
        view_list = []
        map_list = []
        motion_list = []
        target_val_list = []
        target_strat_list = []
        had_real_pov = []
        val_mask_list = []  # True = valid outcome, False = missing (NN-M-12)

        # Per-batch caches to avoid re-querying same match/tick
        _all_players_cache: dict = {}
        _window_cache: dict = {}
        _event_cache: dict = {}
        _metadata_cache: dict = {}
        pov_count = 0

        for i, item in enumerate(raw_items):
            match_id = getattr(item, "match_id", None)
            tick = int(getattr(item, "tick", 0))
            player_name = str(getattr(item, "player_name", ""))
            demo_name = str(getattr(item, "demo_name", ""))

            # Resolve map name (from match metadata or demo_name pattern)
            map_name = self._resolve_map_name(match_id, demo_name, match_mgr, _metadata_cache)

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
                        kb,
                        _all_players_cache,
                        _window_cache,
                        _event_cache,
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

            had_real_pov.append(knowledge is not None)

            # Generate tensors (real POV or legacy zero-fallback)
            map_t = tf.generate_map_tensor(tick_list, map_name, knowledge=knowledge)
            view_t = tf.generate_view_tensor(tick_list, map_name, knowledge=knowledge)
            motion_t = tf.generate_motion_tensor(tick_list, map_name)

            map_list.append(map_t)
            view_list.append(view_t)
            motion_list.append(motion_t)

            # --- Targets ---
            # Advantage function (continuous [0, 1]) when per-match data available
            all_players = _all_players_cache.get((match_id, tick), [])
            if all_players and knowledge is not None:
                val = self._compute_advantage(
                    all_players,
                    str(getattr(item, "team", "CT")),
                    knowledge.bomb_planted,
                )
                val_mask_list.append(True)
            else:
                outcome = getattr(item, "round_outcome", None)
                if outcome is not None:
                    val = float(outcome)
                    val_mask_list.append(True)
                else:
                    val = 0.0  # Placeholder — masked out of loss by val_mask
                    val_mask_list.append(False)
            target_val_list.append(val)

            # Tactical role label (10 classes)
            strat_idx = self._classify_tactical_role(item, knowledge, all_players)
            strat_vec = torch.zeros(10)
            strat_vec[strat_idx] = 1.0
            target_strat_list.append(strat_vec)

        # F3-11: Filter out zero-tensor fallback samples instead of training on garbage
        fallback_count = b - pov_count
        self._total_samples += b
        self._total_fallbacks += fallback_count
        if fallback_count > 0:
            fallback_rate = self._total_fallbacks / max(self._total_samples, 1) * 100
            logger.warning(
                "RAP batch: %d/%d samples fell back to ZERO tensors — dropping them. "
                "Aggregate fallback rate: %.1f%% (%d/%d total)",
                fallback_count,
                b,
                fallback_rate,
                self._total_fallbacks,
                self._total_samples,
            )

            if pov_count == 0:
                logger.warning("Entire RAP batch is zero-tensor fallback. Skipping batch.")
                return None

            # Keep only samples with real POV data
            valid = had_real_pov
            view_list = [v for v, ok in zip(view_list, valid) if ok]
            map_list = [m for m, ok in zip(map_list, valid) if ok]
            motion_list = [m for m, ok in zip(motion_list, valid) if ok]
            target_val_list = [t for t, ok in zip(target_val_list, valid) if ok]
            target_strat_list = [t for t, ok in zip(target_strat_list, valid) if ok]
            val_mask_list = [m for m, ok in zip(val_mask_list, valid) if ok]

            # Re-slice metadata to match filtered samples
            valid_indices = [i for i, ok in enumerate(valid) if ok]
            metadata = features_tensor[valid_indices]
        else:
            logger.debug("RAP batch: %d/%d samples with real Player-POV tensors", pov_count, b)

        view = torch.stack(view_list).to(self.device)
        map_tensor = torch.stack(map_list).to(self.device)
        motion_tensor = torch.stack(motion_list).to(self.device)
        target_val = torch.tensor(target_val_list, dtype=torch.float32).unsqueeze(1).to(self.device)
        target_strat = torch.stack(target_strat_list).to(self.device)
        val_mask = torch.tensor(val_mask_list, dtype=torch.bool).to(self.device)

        return {
            "view": view,
            "map": map_tensor,
            "motion": motion_tensor,
            "metadata": metadata.unsqueeze(1),
            "target_strat": target_strat,
            "target_val": target_val,
            "val_mask": val_mask,  # NN-M-12: True = valid outcome, False = missing
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
