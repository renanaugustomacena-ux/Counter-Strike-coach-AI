import re

import numpy as np
import torch
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, func, select

# B1-XL (2026-07-02): corpora with more eligible ticks than this are sampled
# via seeded id-space rejection instead of materializing every id. The B5
# determinism probes exposed the original B1 fetch OOMing at ~9 minutes on
# the 429M-row monolith (hundreds of millions of Python ints → earlyoom
# SIGTERM, exit 143) — a defect that would equally have killed every G5
# retrain rung. Below the cap the exact-uniform materialization is kept.
_ID_MATERIALIZE_CAP = 2_000_000

from Programma_CS2_RENAN.backend.nn.config import OUTPUT_DIM, RAP_POSITION_SCALE
from Programma_CS2_RENAN.backend.nn.persistence import save_nn
from Programma_CS2_RENAN.backend.nn.train import train_nn
from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator
from Programma_CS2_RENAN.backend.processing.data_pipeline import ProDataPipeline

# --- Clinical Constants ---
from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database
from Programma_CS2_RENAN.backend.storage.db_models import (
    DatasetSplit,
    PlayerMatchStats,
    PlayerProfile,
    PlayerTickState,
)
from Programma_CS2_RENAN.observability.logger_setup import get_logger

app_logger = get_logger("cs2analyzer.nn.coach_manager")

# WR-76: PlayerMatchStats.demo_name is stored as "{stem}.dem_{player}" by legacy ingestion
# (e.g. "falcons-vs-faze-m1-nuke.dem_EliGE"), while PlayerTickState.demo_name stores only
# the stem ("falcons-vs-faze-m1-nuke").  Stripping this suffix at query time keeps both
# tables usable without a DB migration.
_MATCH_STATS_DEMO_SUFFIX_RE = re.compile(r"\.dem_.*$", re.IGNORECASE)

# Tick-level feature names aligned with FeatureExtractor (METADATA_DIM=25).
# Used by the canonical training path (TrainingOrchestrator + StateReconstructor)
TRAINING_FEATURES = [
    # Core vitals (0-4)
    "health",
    "armor",
    "has_helmet",
    "has_defuser",
    "equipment_value",
    # Movement/Stance (5-7)
    "is_crouching",
    "is_scoped",
    "is_blinded",
    # Awareness (8)
    "enemies_visible",
    # Position (9-11)
    "pos_x",
    "pos_y",
    "pos_z",
    # View angles (12-14) - Fixed: sin/cos encoding + pitch
    "view_yaw_sin",
    "view_yaw_cos",
    "view_pitch",
    # Spatial/Contextual (15-18)
    "z_penalty",
    "kast_estimate",
    "map_id",
    "round_phase",
    # Tactical features (19-24) — added in vectorizer expansion
    "weapon_class",
    "time_in_round",
    "bomb_planted",
    "teammates_alive",
    "enemies_alive",
    "team_economy",
]
if len(TRAINING_FEATURES) != METADATA_DIM:
    raise ValueError(f"Feature count mismatch: {len(TRAINING_FEATURES)} vs {METADATA_DIM}")

# Match-aggregate feature names from PlayerMatchStats (used by _prepare_tensors fallback)
# These map to actual DB columns — unlike TRAINING_FEATURES which are tick-level.
# Must be exactly METADATA_DIM (25) entries to avoid zero-padding.
# All fields verified on PlayerMatchStats in db_models.py.
MATCH_AGGREGATE_FEATURES = [
    # Core performance (0-4)
    "avg_kills",
    "avg_deaths",
    "avg_adr",
    "avg_hs",
    "avg_kast",
    # Variance & ratios (5-8)
    "kill_std",
    "adr_std",
    "kd_ratio",
    "impact_rounds",
    # Accuracy & economy (9-11)
    "accuracy",
    "econ_rating",
    "rating",
    # Duel & clutch metrics (12-14)
    "opening_duel_win_pct",
    "clutch_win_pct",
    "trade_kill_ratio",
    # Utility & playstyle (15-17)
    "flash_assists",
    "positional_aggression_score",
    "kpr",
    # HLTV 2.0 components (18-20)
    "dpr",
    "rating_impact",
    "rating_survival",
    # Utility breakdown (21-23)
    "he_damage_per_round",
    "smokes_per_round",
    "unused_utility_per_round",
    # Kill enrichment (24)
    "thrusmoke_kill_pct",
]
if len(MATCH_AGGREGATE_FEATURES) != METADATA_DIM:
    raise ValueError(
        f"MATCH_AGGREGATE_FEATURES length ({len(MATCH_AGGREGATE_FEATURES)}) "
        f"!= METADATA_DIM ({METADATA_DIM})"
    )

TARGET_INDICES = list(range(OUTPUT_DIM))  # First 10 core features targeted by NN adjustments

# Task 2.11.1: Soft Gate - Maturity tiers for calibrating coaching confidence
# Confidence multipliers prevent overconfident coaching when data is sparse
DEMO_TIERS = {
    "CALIBRATING": (0, 50),  # 0-49 demos: Coach is learning, low confidence
    "LEARNING": (50, 200),  # 50-199 demos: Coach is improving, medium confidence
    "MATURE": (200, float("inf")),  # 200+ demos: Full coaching capability
}

TIER_CONFIDENCE = {
    "CALIBRATING": 0.5,  # 50% confidence in recommendations
    "LEARNING": 0.8,  # 80% confidence
    "MATURE": 1.0,  # Full confidence
}


class CoachTrainingManager:
    """
    Orchestrates the "Global wisdom + Local Adaptation" training cycle.
    """

    def __init__(self):
        self.db = get_db_manager()
        self.pipeline = ProDataPipeline()
        self.feature_names = TRAINING_FEATURES
        self.target_indices = TARGET_INDICES

    def check_prerequisites(self) -> tuple[bool, str]:
        """Enforces the 10/10 Rule and Account Connection."""
        try:
            return self._check_db_prerequisites()
        except (SQLAlchemyError, OSError) as e:
            return False, f"Prerequisite Check Failed: {e}"

    def _check_db_prerequisites(self) -> tuple[bool, str]:
        from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

        with self.db.get_session() as session:
            # Check professional demo count (NO ID validation needed)
            p_count = session.exec(
                select(func.count(PlayerMatchStats.id)).where(PlayerMatchStats.is_pro == True)
            ).one()

            # Professional demos can be processed without any user IDs
            # (We analyze all 10 players in the match)
            if p_count >= 10:
                get_state_manager().update_status(
                    "teacher", "Ready", "Professional baseline available. Starting cycle..."
                )
                return True, "Ready"

            # If we don't have enough pro demos yet, check if we can use user demos
            # User demos REQUIRE ID validation (need to filter specific player's ticks)
            profile = session.exec(select(PlayerProfile)).first()
            # 26-SCHEMA-02 (verified 2026-07-02): PlayerProfile has NEVER declared
            # steam_connected/faceit_connected — they live on Ext_PlayerPlaystyle
            # (the DM-02 conflated table) and NO code path writes them anywhere.
            # These getattr reads therefore always yield False today, making the
            # branch below the de-facto only path. Kept defensive-and-False until
            # the connect feature is implemented or the fields are dropped (TASKS#61).
            steam_ok = getattr(profile, "steam_connected", False)
            faceit_ok = getattr(profile, "faceit_connected", False)
            if not profile or not (steam_ok and faceit_ok):
                # If no IDs connected, can only train on pro demos when available
                if p_count > 0:
                    msg = f"Gathering Pro Baseline. Have {p_count}/10 pro demos."
                    get_state_manager().update_status("teacher", "Idle", msg)
                    return False, msg
                else:
                    get_state_manager().update_status(
                        "teacher",
                        "Stalled",
                        "Neural Stall: Connect IDs for user demo analysis OR ingest pro demos",
                    )
                    return (
                        False,
                        "Steam and FACEIT accounts required for user demo analysis. Professional demos can be ingested without IDs.",
                    )

            # IDs are connected - check user demo count
            u_count = session.exec(
                select(func.count(PlayerMatchStats.id)).where(PlayerMatchStats.is_pro == False)
            ).one()

            if u_count < 10:
                msg = f"Need more data. You have {u_count}/10 personal demos."
                get_state_manager().update_status("teacher", "Idle", msg)
                return False, msg

            # Have enough user demos
            if p_count < 10:
                msg = f"Gathering Pro Baseline. Have {p_count}/10 pro demos."
                get_state_manager().update_status("teacher", "Idle", msg)
                return False, msg

        get_state_manager().update_status("teacher", "Ready", "All systems go. Starting cycle...")
        return True, "Ready"

    def increment_maturity_counter(self):
        """Increments the maturity counter after successful demo processing."""
        from Programma_CS2_RENAN.backend.storage.db_models import CoachState

        try:
            with self.db.get_session("knowledge") as s:
                state = s.exec(select(CoachState)).first()
                if not state:
                    state = CoachState()
                    s.add(state)
                state.total_matches_processed += 1
                s.add(state)
                s.commit()
                app_logger.info("Maturity Progress: %s/200", state.total_matches_processed)
        except (SQLAlchemyError, OSError) as e:
            app_logger.error("Maturity Counter Error: %s", e)

    def check_maturity_gate(self) -> tuple[bool, int]:
        """Checks if the coaching system has processed enough demos for reliable advice.

        Implements a SOFT GATE at 50 demos:
        - Below 50: Returns False, UI shows "Calibrating" overlay
        - Above 50: Returns True, full coaching features enabled

        This prevents users from receiving potentially inaccurate coaching advice
        during the initial learning phase when the model hasn't seen enough data.

        Returns:
            tuple[bool, int]: (is_mature, current_count)
        """
        from Programma_CS2_RENAN.backend.storage.db_models import CoachState

        MATURITY_THRESHOLD = 50  # Soft gate threshold

        try:
            with self.db.get_session("knowledge") as s:
                state = s.exec(select(CoachState)).first()
                if not state:
                    return False, 0  # No state = not mature

                count = state.total_matches_processed or 0
                is_mature = count >= MATURITY_THRESHOLD

                if not is_mature:
                    app_logger.debug(
                        "Maturity Gate: Calibrating (%s/%s demos)", count, MATURITY_THRESHOLD
                    )

                return is_mature, count
        except (SQLAlchemyError, OSError) as e:
            app_logger.error("Maturity Gate Error: %s", e)
            return False, 0  # Fail closed on errors

    def get_maturity_tier(self) -> str:
        """
        Task 2.11.1: Returns current maturity tier based on demo count.

        Returns:
            str: 'CALIBRATING' (0-49), 'LEARNING' (50-199), or 'MATURE' (200+)
        """
        _, count = self.check_maturity_gate()

        for tier_name, (min_demos, max_demos) in DEMO_TIERS.items():
            if min_demos <= count < max_demos:
                return tier_name
        return "MATURE"

    def get_confidence_multiplier(self) -> float:
        """
        Task 2.11.1: Returns confidence multiplier based on data maturity.

        Coaching recommendations should be scaled by this multiplier to
        prevent overconfident advice when the model has limited data.

        Returns:
            float: 0.5 (calibrating), 0.8 (learning), or 1.0 (mature)
        """
        tier = self.get_maturity_tier()
        return TIER_CONFIDENCE.get(tier, 1.0)

    def run_full_cycle(self, context=None):
        """Main entry point for the training cycle."""
        try:
            from Programma_CS2_RENAN.observability.sentry_setup import add_breadcrumb

            add_breadcrumb("training", "Full training cycle started")
        except ImportError:
            pass

        from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

        check_passed, reason = self.check_prerequisites()
        if not check_passed:
            get_state_manager().update_status("teacher", "Idle", detail=reason)
            app_logger.warning("ML Training Skipped: %s", reason)
            return

        try:
            init_database()
            get_state_manager().update_status(
                "teacher", "Running", detail="Initializing Training Cycle..."
            )
            app_logger.info("--- ML Cycle Start ---")

            if context:
                context.check_state()

            self.assign_dataset_splits()

            if context:
                context.check_state()
            self._execute_training_phases(context=context)

        except StopIteration:
            raise
        except Exception as e:
            get_state_manager().set_error("teacher", f"Cycle Failed: {e}")
            app_logger.error("Training Cycle Crash: %s", e, exc_info=True)

    def assign_dataset_splits(self):
        """Chronological 70/15/15 split. Prevents temporal data leakage.

        Splits pro and user matches independently to maintain class balance.
        Uses match_date as sort column (indexed in DB).
        Re-assigns ALL matches each cycle so boundaries shift as new data arrives.
        """
        with self.db.get_session() as session:
            total = session.exec(select(func.count(PlayerMatchStats.id))).one()
            if total > 10_000:
                app_logger.warning(
                    "Large match set (%d) in split assignment — "
                    "consider batching if memory pressure occurs.",
                    total,
                )
            all_matches = session.exec(
                select(PlayerMatchStats).order_by(col(PlayerMatchStats.match_date))
            ).all()

            if not all_matches:
                return

            pros = [m for m in all_matches if m.is_pro]
            users = [m for m in all_matches if not m.is_pro]

            def temporal_assign(matches):
                n = len(matches)
                if n == 0:
                    return
                train_idx = int(n * 0.70)
                val_idx = int(n * 0.85)
                for i, m in enumerate(matches):
                    if i < train_idx:
                        m.dataset_split = DatasetSplit.TRAIN
                    elif i < val_idx:
                        m.dataset_split = DatasetSplit.VAL
                    else:
                        m.dataset_split = DatasetSplit.TEST
                    session.add(m)

            temporal_assign(pros)
            temporal_assign(users)
            session.commit()

            total = len(all_matches)
            app_logger.info("Temporal split assigned for %s matches (70/15/15).", total)
            for label, group in [("pro", pros), ("user", users)]:
                if group:
                    train_end_idx = max(0, int(len(group) * 0.70) - 1)
                    app_logger.info(
                        "Temporal split [%s]: %d total, train cutoff date: %s",
                        label,
                        len(group),
                        group[train_end_idx].match_date,
                    )

    def _build_callbacks(self):
        """Build TensorBoard callback registry for Console-driven training."""
        from Programma_CS2_RENAN.backend.nn.training_callbacks import CallbackRegistry

        registry = CallbackRegistry()
        try:
            from Programma_CS2_RENAN.backend.nn.tensorboard_callback import TensorBoardCallback

            tb = TensorBoardCallback(log_dir="runs/console_training")
            registry.add(tb)
            app_logger.info("TensorBoard callback registered for Console training")
        except (ImportError, OSError, RuntimeError) as e:
            app_logger.warning("TensorBoard callback unavailable: %s", e)
        return registry

    def _execute_training_phases(self, context=None):
        from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

        callbacks = self._build_callbacks()

        try:
            get_state_manager().update_status(
                "teacher", "Learning", "Phase 1: JEPA Cognitive Pre-training..."
            )
            self.run_jepa_pretraining(context=context, callbacks=callbacks)

            if context:
                context.check_state()

            get_state_manager().update_status(
                "teacher", "Learning", "Phase 2: Establish Professional Baseline..."
            )
            global_m = self._train_phase(is_pro=True, context=context)
            if not global_m:
                get_state_manager().update_status(
                    "teacher", "Idle", "Failed Professional Baseline Establishment"
                )
                app_logger.error("Failed to establish Professional Baseline.")
                return

            save_nn(global_m, "latest", user_id=None)

            if context:
                context.check_state()

            get_state_manager().update_status(
                "teacher", "Learning", "Phase 3: Tailoring AI to your playstyle..."
            )
            user_m = self._train_phase(is_pro=False, base_model=global_m, context=context)
            if user_m:
                save_nn(user_m, "latest", user_id="user")

            if context:
                context.check_state()

            get_state_manager().update_status(
                "teacher", "Learning", "Phase 4: RAP Behavioral Optimization..."
            )
            self.run_rap_cycle(context=context, callbacks=callbacks)

            if context:
                context.check_state()

            get_state_manager().update_status(
                "teacher", "Learning", "Phase 5: Role Classification Head..."
            )
            self._train_role_head(context=context)

            # Increment maturity after successful training
            self.increment_maturity_counter()

            get_state_manager().update_status(
                "teacher", "Idle", "Training Complete. Knowledge Updated."
            )
        finally:
            callbacks.close_all()

    def run_jepa_pretraining(self, context=None, callbacks=None):
        """
        Phase 1: Self-Supervised Learning on Pro Data.
        Uses Unified Training Orchestrator.
        """
        app_logger.info("Starting JEPA Pre-training via Orchestrator...")
        try:
            orchestrator = TrainingOrchestrator(self, model_type="jepa", callbacks=callbacks)
            orchestrator.run_training(context=context)
        except StopIteration:
            raise
        except ValueError as e:
            app_logger.warning("JEPA Skipping: %s", e)
        except Exception as e:
            app_logger.error("JEPA Training Failed: %s", e)

    def run_rap_cycle(self, context=None, callbacks=None):
        """Phase 4: RAP Behavioral Optimization via Orchestrator."""
        app_logger.info("Starting RAP Optimization via Orchestrator...")
        try:
            orchestrator = TrainingOrchestrator(self, model_type="rap", callbacks=callbacks)
            orchestrator.run_training(context=context)
        except StopIteration:
            raise
        except ValueError as e:
            app_logger.warning("RAP Skipping: %s", e)
        except Exception as e:
            app_logger.error("RAP Training Failed: %s", e)

    def _train_role_head(self, context=None):
        """Phase 5: Train the lightweight role classification neural head."""
        try:
            from Programma_CS2_RENAN.backend.nn.role_head import train_role_head

            if context:
                context.check_state()
            result = train_role_head()
            if result is not None:
                app_logger.info("Role Head training complete.")
            else:
                app_logger.info("Role Head training skipped (insufficient data).")
        except StopIteration:
            raise
        except Exception as e:
            app_logger.warning("Role Head training failed (non-fatal): %s", e)

    def _fetch_jepa_ticks(
        self,
        is_pro: bool,
        split: DatasetSplit = DatasetSplit.TRAIN,
        seed: int = 42,
        sample_size: int = 5000,
    ):
        """Fetch ticks for JEPA/RAP training with seeded subsampling.

        B1: Each call with a different ``seed`` returns a different random
        subsample of ``sample_size`` ticks from the eligible pool.  This is the
        mechanism that gives each epoch a fresh data window while keeping any
        single call deterministic (DET-01).

        P4-A: Only uses demos whose per-match DB is marked match_complete=True,
        preventing Teacher from training on half-written match data.
        """
        completed_demos = self._get_completed_demo_names()

        with self.db.get_session() as session:
            stmt_matches = select(PlayerMatchStats).where(
                PlayerMatchStats.is_pro == is_pro, PlayerMatchStats.dataset_split == split
            )
            matches = session.exec(stmt_matches).all()

            if not matches:
                app_logger.warning("No %s matches found for is_pro=%s", split, is_pro)
                return []

            # WR-76: Strip legacy ".dem_{player}" suffix
            all_demo_names = set(
                _MATCH_STATS_DEMO_SUFFIX_RE.sub("", m.demo_name) for m in matches if m.demo_name
            )
            if completed_demos is not None:
                demo_names = list(all_demo_names & completed_demos)
                skipped = len(all_demo_names) - len(demo_names)
                if skipped > 0:
                    app_logger.info(
                        "P4-A: Skipped %d incomplete demos (match_complete=False)", skipped
                    )
            else:
                demo_names = list(all_demo_names)

            if not demo_names:
                app_logger.warning("No eligible demos for %s split (is_pro=%s)", split, is_pro)
                return []

            # B1: seeded subsampling so each epoch sees a fresh corpus window.
            # B1-XL: the id list is only "lightweight" on small corpora — on
            # the full monolith it OOMs (see _ID_MATERIALIZE_CAP note), so the
            # strategy is chosen by a COUNT first (returns one integer, never
            # materializes rows).
            eligibility = col(PlayerTickState.demo_name).in_(demo_names)

            # B1-XL cache: the eligibility COUNT (and min/max id) walk ~10^8
            # index entries — ~25 minutes on the full monolith. B1 re-fetches
            # train data EVERY epoch, so without this cache a 5-epoch smoke
            # rung pays that price five times over for a corpus that cannot
            # change mid-run (ingestion never runs concurrently with training
            # per the concurrency policy). Cache lives on the manager instance
            # → scoped to one training process, cold again next run.
            scale_cache = getattr(self, "_fetch_scale_cache", None)
            if scale_cache is None:
                scale_cache = {}
                self._fetch_scale_cache = scale_cache
            cache_key = (is_pro, str(split), tuple(sorted(demo_names)))
            scale = scale_cache.get(cache_key)
            if scale is None:
                total = session.exec(
                    select(func.count()).select_from(PlayerTickState).where(eligibility)
                ).one()
                if total > _ID_MATERIALIZE_CAP:
                    id_min = session.exec(
                        select(func.min(PlayerTickState.id)).where(eligibility)
                    ).one()
                    id_max = session.exec(
                        select(func.max(PlayerTickState.id)).where(eligibility)
                    ).one()
                else:
                    id_min = id_max = None
                scale = (total, id_min, id_max)
                scale_cache[cache_key] = scale
            total, _cached_id_min, _cached_id_max = scale

            # Fallback for legacy data without demo_name
            if not total:
                app_logger.warning("No ticks found with demo_name filter, using LIMIT fallback")
                fallback_stmt = select(PlayerTickState).limit(min(sample_size, 1000))
                ticks = session.exec(fallback_stmt).all()
                app_logger.info("Loaded %s ticks for %s split (fallback)", len(ticks), split)
                return ticks

            rng = np.random.default_rng(seed)
            n_select = min(sample_size, total)

            if total <= _ID_MATERIALIZE_CAP:
                id_stmt = select(PlayerTickState.id).where(eligibility)
                all_ids = [row for row in session.exec(id_stmt).all()]
                selected_ids = rng.choice(all_ids, size=n_select, replace=False).tolist()
                app_logger.info(
                    "B1: Sampling %d/%d ticks for %s split (seed=%d, is_pro=%s)",
                    n_select,
                    total,
                    split,
                    seed,
                    is_pro,
                )
            else:
                id_min, id_max = _cached_id_min, _cached_id_max
                selected_ids = self._sample_ids_rejection(
                    session, demo_names, rng, n_select, id_min, id_max, total
                )
                app_logger.info(
                    "B1-XL: Sampled %d/%d ticks for %s split via id-space rejection "
                    "(seed=%d, is_pro=%s)",
                    len(selected_ids),
                    total,
                    split,
                    seed,
                    is_pro,
                )

            # Fetch full objects for selected IDs (chunked for SQLite safety)
            _CHUNK = 500
            ticks = []
            for chunk_start in range(0, len(selected_ids), _CHUNK):
                chunk_ids = selected_ids[chunk_start : chunk_start + _CHUNK]
                chunk_stmt = select(PlayerTickState).where(col(PlayerTickState.id).in_(chunk_ids))
                ticks.extend(session.exec(chunk_stmt).all())

            app_logger.info("Loaded %s ticks for %s split", len(ticks), split)
            return ticks

    def _sample_ids_rejection(self, session, demo_names, rng, n_select, id_min, id_max, total):
        """B1-XL: seeded id-space rejection sampling — RAM stays O(n_select).

        Deterministic (DET-01/B1): candidates come from the seeded rng in a
        fixed order and acceptance preserves that order, so a given
        (seed, corpus) always yields the same ids. The distribution is
        uniform over the id RANGE rather than the exact row set — primary-key
        gaps introduce negligible bias for a training subsample, a deliberate
        trade against materializing hundreds of millions of ids.
        """
        span = max(1, id_max - id_min + 1)
        density = total / span
        # Draw budget: comfortably above expectation, hard-capped so a
        # pathologically sparse id range can never loop unbounded.
        expected_draws = n_select / max(density, 1e-9)
        max_candidates = int(min(max(expected_draws * 8, n_select * 4), 5_000_000))
        eligibility = col(PlayerTickState.demo_name).in_(demo_names)

        selected: list = []
        seen: set = set()
        drawn = 0
        _DRAW_BATCH = 5000
        _QUERY_CHUNK = 500
        while len(selected) < n_select and drawn < max_candidates:
            batch = rng.integers(id_min, id_max + 1, size=_DRAW_BATCH)
            drawn += _DRAW_BATCH
            # Preserve draw order and drop repeats — order is what makes the
            # accepted set reproducible for a given seed.
            ordered = []
            for c in batch:
                c = int(c)
                if c not in seen:
                    seen.add(c)
                    ordered.append(c)
            if not ordered:
                continue
            found: set = set()
            for i in range(0, len(ordered), _QUERY_CHUNK):
                chunk = ordered[i : i + _QUERY_CHUNK]
                rows = session.exec(
                    select(PlayerTickState.id).where(
                        col(PlayerTickState.id).in_(chunk), eligibility
                    )
                ).all()
                found.update(int(r) for r in rows)
            selected.extend(c for c in ordered if c in found)

        if len(selected) < n_select:
            app_logger.warning(
                "B1-XL: rejection sampling underfilled %d/%d after %d candidates "
                "(id-range density %.4f) — proceeding with the smaller subsample",
                len(selected),
                n_select,
                drawn,
                density,
            )
        return selected[:n_select]

    def _fetch_jepa_windows(
        self,
        is_pro: bool,
        split: DatasetSplit = DatasetSplit.TRAIN,
        seed: int = 42,
        n_windows: int = 4500,
        window_len: int = 11,
    ):
        """Fetch temporally-contiguous single-player windows for JEPA training.

        R4 CRIT (2026-07-16): the JEPA consumer builds (context, target) as
        positional slices of its batch — rows 0..9 are the context, row 10 the
        next-step target. The old flat ``_fetch_jepa_ticks`` feed returned
        randomly-subsampled, unordered rows spanning players and demos, so
        "next-step prediction" was trained on unrelated pairs (a plausible
        cause of the ~1.90 val-loss plateau). This fetcher keeps the whole
        B1/B1-XL/P4-A/DET-01 machinery by reusing ``_fetch_jepa_ticks`` as a
        seeded ANCHOR sampler, then expands each anchor into ``window_len``
        contiguous ticks of the SAME (demo, player) stream.

        Returns:
            List[List[PlayerTickState]]: one inner list (len == window_len,
            same player, ascending ticks) per window. Anchors too close to
            the end of their player's stream are dropped (logged).
        """
        anchors = self._fetch_jepa_ticks(
            is_pro=is_pro, split=split, seed=seed, sample_size=n_windows
        )
        if not anchors:
            return []

        windows: list = []
        with self.db.get_session() as session:
            for anchor in anchors:
                rows = session.exec(
                    select(PlayerTickState)
                    .where(
                        PlayerTickState.demo_name == anchor.demo_name,
                        PlayerTickState.player_name == anchor.player_name,
                        PlayerTickState.tick >= anchor.tick,
                    )
                    .order_by(PlayerTickState.tick)
                    .limit(window_len)
                ).all()
                if len(rows) == window_len:
                    windows.append(list(rows))

        dropped = len(anchors) - len(windows)
        app_logger.info(
            "JEPA windows: %d contiguous single-player windows of %d ticks "
            "(%d end-of-stream anchors dropped, seed=%d, %s split)",
            len(windows),
            window_len,
            dropped,
            seed,
            split,
        )
        return windows

    def _fetch_rap_windows(
        self,
        is_pro: bool,
        split: DatasetSplit = DatasetSplit.TRAIN,
        window_size: int = 96,
        max_demos: int | None = None,
    ):
        """Fetch windowed tick data for RAP training from completed matches.

        Unlike JEPA's flat tick fetcher, RAP needs contiguous temporal windows
        of a SINGLE player's POV stream.  This method:
        1. Fetches only completed matches (match_complete == True)
        2. Loads ticks from the monolith grouped by (demo, player)
        3. Segments each player's run into contiguous windows of *window_size*

        Each returned window is a list of PlayerTickState objects from a single
        demo AND a single player, ordered by tick. R4 CRIT (2026-07-16):
        ordering by tick alone interleaved all 10 players' rows, so the RAP
        consumers (_rap_compute_target_pos position deltas, LTC timespans)
        were computed BETWEEN DIFFERENT PLAYERS — garbage training signal.

        Returns:
            List[List[PlayerTickState]]: one inner list per window.
        """
        completed_demos = self._get_completed_demo_names()

        with self.db.get_session() as session:
            stmt = select(PlayerMatchStats).where(
                PlayerMatchStats.is_pro == is_pro,
                PlayerMatchStats.dataset_split == split,
            )
            matches = session.exec(stmt).all()
            if not matches:
                app_logger.warning("No %s matches for RAP (is_pro=%s)", split, is_pro)
                return []

            # WR-76 (R4 HIGH): PlayerMatchStats stores legacy "stem.dem_Player"
            # names while PlayerTickState stores the bare stem — same strip as
            # _fetch_jepa_ticks, without which the completed-demos intersection
            # and the tick query silently match nothing on legacy data.
            all_demo_names = {
                _MATCH_STATS_DEMO_SUFFIX_RE.sub("", m.demo_name) for m in matches if m.demo_name
            }
            if completed_demos is not None:
                demo_names = sorted(all_demo_names & completed_demos)
                skipped = len(all_demo_names) - len(demo_names)
                if skipped > 0:
                    app_logger.info("P7: Skipped %d incomplete demos for RAP windows", skipped)
            else:
                demo_names = sorted(all_demo_names)

            if not demo_names:
                app_logger.warning("No completed demos available for RAP windows")
                return []

            if max_demos is not None and len(demo_names) > max_demos:
                app_logger.info("RAP demo cap: %d → %d demos", len(demo_names), max_demos)
                demo_names = demo_names[:max_demos]

            windows: list = []
            # Historical budget was 10k interleaved rows per demo (~1k ticks
            # per player at 10 players) — kept equivalent per player.
            _PER_PLAYER_TICK_CAP = 1_000

            for demo_name in demo_names:
                player_names = sorted(
                    p
                    for p in session.exec(
                        select(PlayerTickState.player_name)
                        .where(PlayerTickState.demo_name == demo_name)
                        .distinct()
                    ).all()
                    if p
                )
                for player_name in player_names:
                    ticks = list(
                        session.exec(
                            select(PlayerTickState)
                            .where(
                                PlayerTickState.demo_name == demo_name,
                                PlayerTickState.player_name == player_name,
                            )
                            .order_by(PlayerTickState.tick)
                            .limit(_PER_PLAYER_TICK_CAP)
                        ).all()
                    )

                    # T-1 + V-5 FIX: Skip player runs shorter than one full
                    # segmentation window (window_size, not a magic 32) —
                    # shorter runs would produce zero windows (dead I/O).
                    if len(ticks) < window_size:
                        continue

                    # Segment into non-overlapping contiguous windows
                    for i in range(0, len(ticks) - window_size + 1, window_size):
                        windows.append(ticks[i : i + window_size])

            app_logger.info(
                "RAP windows: %d single-player windows of %d ticks from %d demos (%s split)",
                len(windows),
                window_size,
                len(demo_names),
                split,
            )
            return windows

    @staticmethod
    def _get_completed_demo_names():
        """P4-A: Return set of demo_names whose per-match DB has match_complete=True.

        Returns None if match data manager is unavailable (graceful degradation).
        """
        try:
            from Programma_CS2_RENAN.backend.storage.match_data_manager import (
                get_match_data_manager,
            )

            mdm = get_match_data_manager()
            completed = set()
            for match_id in mdm.list_available_matches():
                meta = mdm.get_metadata(match_id)
                if meta and getattr(meta, "match_complete", False):
                    completed.add(meta.demo_name)
            return completed if completed else None
        except (SQLAlchemyError, OSError, AttributeError) as e:
            app_logger.debug("P4-A: match completeness check unavailable: %s", e)
            return None

    def _train_phase(self, is_pro=True, base_model=None, context=None):
        train_data = self._fetch_training_data(is_pro, split="train")
        val_data = self._fetch_training_data(is_pro, split="val")
        if len(train_data) < 2:
            return None
        X_train, y_train = self._prepare_tensors(train_data)
        X_val, y_val = self._prepare_tensors(val_data) if val_data else (X_train, y_train)
        return train_nn(
            X_train, y_train, X_val=X_val, y_val=y_val, model=base_model, context=context
        )

    def _update_state(self, status, detail):
        """Internal helper for Orchestrator to update global state."""
        from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

        get_state_manager().update_status("teacher", status, detail=detail)

    def _fetch_training_data(self, is_pro, split="train"):
        with self.db.get_session() as session:
            stmt = select(PlayerMatchStats).where(
                PlayerMatchStats.is_pro == is_pro, PlayerMatchStats.dataset_split == split
            )
            return session.exec(stmt).all()

    def _prepare_tensors(self, raw_data):
        X, y = [], []
        pro_vec = self._get_pro_baseline_vector()
        for item in raw_data:
            stats = item.model_dump()
            # Extract all 25 match-aggregate features (actual DB columns, no zero-padding needed).
            # Explicit None guard: dict.get(key, default) returns None when the key
            # exists with a NULL DB value, which would produce NaN in the tensor.
            vec = np.array(
                [
                    (v if (v := stats.get(f, 0.0)) is not None else 0.0)
                    for f in MATCH_AGGREGATE_FEATURES
                ],
                dtype=np.float32,
            )
            X.append(vec)
            y.append(self._calculate_deltas(vec, pro_vec))
        X_t = torch.tensor(np.array(X, dtype=np.float32), dtype=torch.float32)
        y_t = torch.tensor(np.array(y, dtype=np.float32), dtype=torch.float32)
        return X_t, y_t

    def _calculate_deltas(self, vec, pro_vec):
        """
        Calculate improvement deltas with Z-score normalization.
        This prevents features with larger magnitudes (ADR: 80-120) from
        dominating features with smaller scales (deaths: 0.5-0.6).
        """
        # Feature-specific scale factors (approximate standard deviations)
        # These should ideally be computed from training data, but static values work for MVP
        FEATURE_SCALES = {
            "avg_kills": 0.15,
            "avg_deaths": 0.12,
            "avg_adr": 12.0,
            "avg_hs": 0.10,
            "avg_kast": 0.08,
            "rating": 0.12,
            "kill_std": 0.08,
            "adr_std": 8.0,
            "kd_ratio": 0.20,
            "impact_rounds": 0.10,
            "accuracy": 0.05,
            "econ_rating": 0.15,
            "opening_duel_win_pct": 0.12,
            "clutch_win_pct": 0.10,
            "trade_kill_ratio": 0.10,
            "flash_assists": 0.08,
            "positional_aggression_score": 0.15,
            "kpr": 0.08,
            "dpr": 0.06,
            "rating_impact": 0.15,
            "rating_survival": 0.10,
            "he_damage_per_round": 5.0,
            "smokes_per_round": 0.15,
            "unused_utility_per_round": 0.20,
            "thrusmoke_kill_pct": 0.05,
        }
        default_scale = 0.15

        deltas = []
        for idx in self.target_indices:
            target = pro_vec[idx]
            current = vec[idx]

            # Get feature-specific scale for normalization (use match-aggregate names)
            feat_name = (
                MATCH_AGGREGATE_FEATURES[idx] if idx < len(MATCH_AGGREGATE_FEATURES) else None
            )
            scale = FEATURE_SCALES.get(feat_name, default_scale)

            # Z-score normalized delta: (target - current) / scale
            delta = (target - current) / (scale + 1e-6)
            deltas.append(np.clip(delta, -1, 1))
        return deltas

    def _get_pro_baseline_vector(self):
        from Programma_CS2_RENAN.backend.processing.baselines.pro_baseline import get_pro_baseline

        baseline = get_pro_baseline()

        # Build baseline vector aligned with MATCH_AGGREGATE_FEATURES (25 entries, no padding)
        defaults = {
            "avg_kills": 0.75,
            "avg_deaths": 0.65,
            "avg_adr": 80.0,
            "avg_hs": 0.50,
            "avg_kast": 0.72,
            "kill_std": 0.15,
            "adr_std": 12.0,
            "kd_ratio": 1.15,
            "impact_rounds": 0.7,
            "accuracy": 0.50,
            "econ_rating": 0.75,
            "rating": 1.05,
            "opening_duel_win_pct": 0.50,
            "clutch_win_pct": 0.10,
            "trade_kill_ratio": 0.15,
            "flash_assists": 0.10,
            "positional_aggression_score": 0.50,
            "kpr": 0.75,
            "dpr": 0.65,
            "rating_impact": 1.10,
            "rating_survival": 0.35,
            "he_damage_per_round": 5.0,
            "smokes_per_round": 0.40,
            "unused_utility_per_round": 0.30,
            "thrusmoke_kill_pct": 0.02,
        }
        vec = []
        for feat in MATCH_AGGREGATE_FEATURES:
            if feat in baseline:
                val = baseline[feat]
                vec.append(val["mean"] if isinstance(val, dict) else float(val))
            else:
                vec.append(defaults.get(feat, 0.0))
        return np.array(vec, dtype=np.float32)

    def get_skill_radar_data(self):
        """Generates skill delta comparison for UI radar visualization.

        Returns:
            dict: {"status": str, "data": dict, "maturity_progress": int}
        """
        is_mature, count = self.check_maturity_gate()

        if not is_mature:
            return {
                "status": "calibrating",
                "message": f"Coach is still learning. {count}/200 demos processed.",
                "maturity_progress": count,
                "data": {},
            }

        try:
            from Programma_CS2_RENAN.backend.processing.baselines.pro_baseline import (
                get_pro_baseline,
            )

            # Skill radar uses match-level aggregates (PlayerMatchStats fields),
            # NOT tick-level TRAINING_FEATURES. Query DB directly.
            SKILL_METRICS = {
                "ADR": ("avg_adr", 80.0),
                "Impact": ("impact_rounds", 0.7),
                "KAST": ("avg_kast", 0.72),
                "Accuracy": ("accuracy", 0.50),
                "Rating": ("rating", 1.05),
                "Economy": ("econ_rating", 0.75),
            }

            # Get user averages from match stats (F3-22: bounded query)
            _RADAR_MATCH_LIMIT = 5000
            with self.db.get_session() as session:
                user_matches = session.exec(
                    select(PlayerMatchStats)
                    .where(PlayerMatchStats.is_pro == False)
                    .order_by(col(PlayerMatchStats.match_date).desc())
                    .limit(_RADAR_MATCH_LIMIT)
                ).all()

            # Get pro baseline
            pro_baseline = get_pro_baseline()

            radar_data = {}
            for skill, (field, fallback) in SKILL_METRICS.items():
                # User average for this metric
                user_vals = [getattr(m, field, 0.0) for m in user_matches if hasattr(m, field)]
                user_avg = float(np.mean(user_vals)) if user_vals else 0.0

                # Pro reference for this metric
                if field in pro_baseline and isinstance(pro_baseline[field], dict):
                    pro_avg = pro_baseline[field].get("mean", fallback)
                elif field in pro_baseline:
                    pro_avg = float(pro_baseline[field])
                else:
                    pro_avg = fallback

                delta = ((user_avg - pro_avg) / (pro_avg + 1e-6)) * 100
                radar_data[skill] = float(np.clip(delta, -100, 100))

            return {"status": "success", "data": radar_data, "maturity_progress": count}
        except Exception as e:
            app_logger.error("Skill Radar Error: %s", e)
            return {"status": "error", "message": str(e), "data": {}}

    def _get_user_baseline_vector(self):
        """Fetches user's average performance across all personal demos."""
        user_data = self._fetch_training_data(is_pro=False, split="train")
        if not user_data or len(user_data) < 5:
            return self._get_pro_baseline_vector()  # Fallback to pro if insufficient data

        vecs = [
            np.array(
                [
                    (v if (v := item.model_dump().get(f, 0.0)) is not None else 0.0)
                    for f in MATCH_AGGREGATE_FEATURES
                ],
                dtype=np.float32,
            )
            for item in user_data
        ]
        return np.mean(vecs, axis=0)

    def get_interactive_overlay_data(self, match_id: int):
        """Generates tick-by-tick advantage and ghost position data for 2D viewer.

        Args:
            match_id: The match ID to analyze

        Returns:
            dict: {"status": str, "overlay_results": dict, "maturity_progress": int}
        """
        from Programma_CS2_RENAN.core.config import get_setting

        if not get_setting("USE_RAP_MODEL", default=False):
            return {
                "status": "disabled",
                "message": "RAP model is experimental and disabled by default. "
                "Enable via USE_RAP_MODEL=True in settings.",
                "overlay_results": {},
            }

        is_mature, count = self.check_maturity_gate()

        if not is_mature:
            return {
                "status": "calibrating",
                "message": f"Professional Correction locked. {count}/200 demos processed.",
                "maturity_progress": count,
                "overlay_results": {},
            }

        try:
            from Programma_CS2_RENAN.backend.nn.config import get_device
            from Programma_CS2_RENAN.backend.nn.experimental.rap_coach.model import RAPCoachModel
            from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError, load_nn
            from Programma_CS2_RENAN.backend.processing.state_reconstructor import (
                RAPStateReconstructor,
            )

            device = get_device()

            model = RAPCoachModel()
            try:
                load_nn("rap_coach", model)
            except (StaleCheckpointError, FileNotFoundError):
                app_logger.warning(
                    "RAP checkpoint missing or stale (architecture changed). "
                    "Overlay unavailable until model is trained."
                )
                return {
                    "status": "error",
                    "message": "Model checkpoint missing or outdated — training required.",
                    "overlay_results": {},
                }
            model.to(device)

            model.eval()  # Ensure eval mode
            reconstructor = RAPStateReconstructor()

            # Fetch ticks for this match
            with self.db.get_session() as s:
                stmt = select(PlayerTickState).where(PlayerTickState.match_id == match_id)
                ticks = s.exec(stmt).all()

            if not ticks:
                return {
                    "status": "error",
                    "message": "No tick data for this match",
                    "overlay_results": {},
                }

            windows = reconstructor.segment_match_into_windows(ticks)
            overlay_results = {}

            for window in windows:
                batch = reconstructor.reconstruct_belief_tensors(window)
                for k, v in batch.items():
                    if isinstance(v, torch.Tensor):
                        batch[k] = v.to(device)

                with torch.no_grad():
                    outputs = model(
                        view_frame=batch["view"],
                        map_frame=batch["map"],
                        motion_diff=batch["motion"],
                        metadata=batch["metadata"],
                    )

                # Extract advantage and ghost position for each tick in window
                for tick in window:
                    advantage = float(outputs["value_estimate"].cpu().numpy()[0])
                    # POS-2D: Model outputs [dx, dy, dz]; Z-axis unused (2D map coordinates).
                    optimal_pos = outputs["optimal_pos"].cpu().numpy()[0]
                    attribution = outputs["attribution"].cpu().numpy()[0]  # [5] contents

                    # Convert normalized deltas to world coordinates
                    ghost_x = tick.pos_x + (optimal_pos[0] * RAP_POSITION_SCALE)
                    ghost_y = tick.pos_y + (optimal_pos[1] * RAP_POSITION_SCALE)

                    overlay_results[tick.tick] = {
                        "advantage": advantage,
                        "ghost_pos": {tick.player_name: (ghost_x, ghost_y)},
                        "attribution": attribution.tolist(),
                    }

            return {
                "status": "success",
                "overlay_results": overlay_results,
                "maturity_progress": count,
            }
        except Exception as e:
            app_logger.error("Overlay Data Error: %s", e)
            return {"status": "error", "message": str(e), "overlay_results": {}}


def _fetch_rap_ticks(db):
    from Programma_CS2_RENAN.core.config import get_setting

    current_name = get_setting("CS2_PLAYER_NAME")
    with db.get_session() as s:
        stmt = select(PlayerTickState).where(PlayerTickState.player_name == current_name)
        return s.exec(stmt).all()


def _train_on_windows(trainer, windows, reconstructor, device):
    list(map(lambda w: _process_single_rap_window(trainer, w, reconstructor, device), windows))
    app_logger.info("RAP-Coach complete.")


def _process_single_rap_window(trainer, w, recon, device):
    batch = recon.reconstruct_belief_tensors(w)
    for k, v in batch.items():
        if isinstance(v, torch.Tensor):
            batch[k] = v.to(device)
    _apply_dynamic_window_targets(batch, w)
    trainer.train_step(batch)


def _apply_dynamic_window_targets(batch, window_ticks):
    # NOTE (F3-28): Taking the mean of round_outcome across a temporal window creates
    # an implicit label-smoothing effect. If the window spans a round boundary (loss→win),
    # the target becomes ~0.5 — an uninformative gradient signal. Acceptable for the
    # current prototype; a round-boundary-aware windowing strategy would improve label quality.
    outcomes = [t.round_outcome for t in window_ticks if t.round_outcome is not None]
    val = np.mean(outcomes) if outcomes else 0.5
    batch["target_val"] = torch.tensor([[float(val)]], dtype=torch.float32)
    strat = np.mean([t.equipment_value / 10000.0 for t in window_ticks])
    t_strat = torch.zeros(1, 10)
    strat_idx = min(int(strat * 9), 9)  # Clamp to valid index range [0, 9]
    t_strat[0, strat_idx] = 1.0
    batch["target_strat"] = t_strat


def _calculate_pro_mean(pro_raw, feature_names):
    rows = [_extract_feature_vector(p, feature_names) for p in pro_raw]
    return np.mean(rows, axis=0)


def _extract_feature_vector(p, feature_names):
    d = p.model_dump()
    return [d.get(f, 0) for f in feature_names]


if __name__ == "__main__":
    CoachTrainingManager().run_full_cycle()
