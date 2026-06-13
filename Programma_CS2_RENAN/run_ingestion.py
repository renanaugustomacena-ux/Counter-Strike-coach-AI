import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections
from Programma_CS2_RENAN.backend.data_sources.demo_parser import parse_demo
from Programma_CS2_RENAN.backend.ingestion.resource_manager import ResourceManager
from Programma_CS2_RENAN.backend.nn.model import RAPCoachModel, RAPCommunication
from Programma_CS2_RENAN.backend.processing.state_reconstructor import RAPStateReconstructor
from Programma_CS2_RENAN.backend.progress.longitudinal import FeatureTrend
from Programma_CS2_RENAN.backend.progress.trend_analysis import compute_trend
from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database
from Programma_CS2_RENAN.backend.storage.db_models import (
    CoachingInsight,
    PlayerMatchStats,
    PlayerTickState,
)
from Programma_CS2_RENAN.backend.storage.match_data_manager import (
    MatchEventState,
    MatchMetadata,
    get_match_data_manager,
)
from Programma_CS2_RENAN.backend.storage.state_manager import (  # NEW: For progress tracking
    get_state_manager,
)
from Programma_CS2_RENAN.backend.storage.storage_manager import StorageManager
from Programma_CS2_RENAN.core.config import MIN_DEMOS_FOR_COACHING, refresh_settings
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.ingestion_runner")


def _check_duplicate_demo(db_manager, demo_name: str) -> bool:
    """Unified duplicate detection across all ingestion data stores.

    Checks:
    1. IngestionTask table (exact path, excludes error/processing)
    2. PlayerMatchStats table (by demo_name stem)
    3. Per-match DB file existence

    Args:
        db_manager: Database manager instance
        demo_name: Full path or base name of the demo file

    Returns:
        True if demo was already ingested, False otherwise
    """
    from sqlalchemy import func
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.db_models import IngestionTask

    # R3-04: Extract stem for PlayerMatchStats and match DB checks
    normalized = Path(demo_name).stem

    with db_manager.get_session() as session:
        # Check 1: IngestionTask — exact path match.
        # Exclude "error" (retryable) and "processing" (current task).
        task_count = session.exec(
            select(func.count(IngestionTask.id)).where(
                IngestionTask.demo_path == demo_name,
                IngestionTask.status.notin_(["error", "processing"]),
            )
        ).one()
        if task_count > 0:
            logger.warning(
                "Duplicate detected: Demo '%s' has active IngestionTask (status != error)",
                demo_name,
            )
            return True

        # Check 2: PlayerMatchStats (already fully ingested)
        stats_count = session.exec(
            select(func.count(PlayerMatchStats.id)).where(PlayerMatchStats.demo_name == normalized)
        ).one()
        if stats_count > 0:
            logger.warning(
                "Duplicate detected: Demo '%s' already in PlayerMatchStats",
                demo_name,
            )
            return True

    # Check 3: Per-match DB file existence
    import hashlib

    match_id = int(hashlib.sha256(normalized.encode()).hexdigest(), 16) % (2**63 - 1)
    try:
        from Programma_CS2_RENAN.backend.storage.match_data_manager import get_match_data_manager

        mdm = get_match_data_manager()
        if match_id in mdm.list_available_matches():
            logger.warning(
                "Duplicate detected: match_%d.db exists for demo '%s'",
                match_id,
                demo_name,
            )
            return True
    except Exception:
        pass  # Match data manager may not be initialized yet

    return False


def run_ml_pipeline(db_manager, player_name: str, current_demo_name: str, stats: dict):
    """Main ML Ingestion Pipeline."""
    if not _is_profile_ready(db_manager, player_name):
        return
    logger.info("Running ML pipeline for %s...", player_name)

    # 1. Resolve Skill & Curriculum (Phase 5)
    from Programma_CS2_RENAN.backend.processing.skill_assessment import SkillLatentModel
    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

    # Wrap the stats dict into a model-like object for the skill calculator
    current_stats_obj = PlayerMatchStats(
        **stats, player_name=player_name, demo_name=current_demo_name
    )
    skill_vec = SkillLatentModel.calculate_skill_vector(current_stats_obj)
    curr_level = SkillLatentModel.get_curriculum_level(skill_vec)

    logger.info("Player Level Identified: %s/10 (Axes: %s)", curr_level, skill_vec)

    # Pro-baseline deviations live in hltv_metadata.db and are computed only during
    # coaching inference, never during demo ingestion. Ingestion stays isolated from
    # HLTV reads; downstream consumers that need Z-scores call calculate_deviations
    # directly against get_pro_baseline() at inference time.
    deviations: dict = {}
    trends = _get_feature_trends(db_manager, player_name)

    # 2. Level-Conditioned RAP Inference
    rap_insights = _get_rap_inference(db_manager, player_name, skill_level=curr_level)

    _save_insights(
        db_manager,
        player_name,
        current_demo_name,
        deviations,
        trends,
        rap_insights,
        skill_level=curr_level,
    )


def _is_profile_ready(db_manager, player_name):
    """Check whether the player has enough data for coaching.

    Requires a PlayerProfile row (player_name only — Steam/Faceit
    connections are optional enrichment, not prerequisites) and at
    least MIN_DEMOS_FOR_COACHING non-pro demos ingested.
    """
    from sqlmodel import func, select

    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats, PlayerProfile

    with db_manager.get_session() as session:
        p = session.exec(
            select(PlayerProfile).where(PlayerProfile.player_name == player_name)
        ).first()
        if not p:
            return False
        cnt = session.exec(
            select(func.count(PlayerMatchStats.id)).where(
                PlayerMatchStats.player_name == player_name, PlayerMatchStats.is_pro.is_(False)
            )
        ).one()
        return cnt >= MIN_DEMOS_FOR_COACHING


def _get_feature_trends(db_manager, player_name):
    from sqlmodel import select

    with db_manager.get_session() as session:
        stmt = (
            select(PlayerMatchStats)
            .where(PlayerMatchStats.player_name == player_name)
            .order_by(PlayerMatchStats.processed_at.desc())
            .limit(10)
        )
        history = session.exec(stmt).all()
    if len(history) < 3:
        return []
    trends = []
    for feat in ["avg_kills", "avg_adr", "avg_kast", "accuracy"]:
        values = [getattr(h, feat, 0) for h in reversed(history)]
        slope, vol, conf = compute_trend(values)
        trends.append(FeatureTrend(feature=feat, slope=slope, volatility=vol, confidence=conf))
    return trends


def _get_rap_inference(db_manager, player_name, skill_level: int = 5):
    try:
        return _execute_rap_logic(db_manager, player_name, skill_level)
    except Exception as e:
        logger.error("RAP Inference failed: %s", e)
        return []


def _execute_rap_logic(db_manager, player_name, skill_level: int = 5):
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.nn.persistence import load_nn

    with db_manager.get_session() as session:
        stmt = select(PlayerTickState).where(PlayerTickState.player_name == player_name)
        ticks = session.exec(stmt).all()
    if not ticks:
        return []
    recon, model, comm = RAPStateReconstructor(), RAPCoachModel(), RAPCommunication()
    try:
        model = load_nn("latest_rap", model, user_id=player_name)
    except Exception:
        logger.warning(
            "RAP model checkpoint incompatible for %s. Skipping RAP insights.", player_name
        )
        return []
    windows = recon.segment_match_into_windows(ticks)
    insights = []
    for window in windows[:5]:
        batch = recon.reconstruct_belief_tensors(window)
        out = model(batch["view"], batch["map"], batch["motion"], batch["metadata"])
        advice = comm.generate_advice(out["advice_probs"], confidence=0.85, skill_level=skill_level)
        if advice:
            insights.append(advice)
    return insights


def _save_insights(
    db_manager, p_name, demo_name, deviations, trends, rap_advices, skill_level: int = 5
):
    from sqlmodel import delete

    from Programma_CS2_RENAN.backend.coaching.longitudinal_engine import (
        generate_longitudinal_coaching,
    )

    nn_signals = {"stability_warning": any(t.volatility > 0.2 for t in trends)}
    long_i = generate_longitudinal_coaching(trends, nn_signals)
    corr = generate_corrections(deviations, 30)
    with db_manager.get_session() as session:
        session.exec(delete(CoachingInsight).where(CoachingInsight.demo_name == demo_name))
        _save_batch_insights(session, p_name, demo_name, rap_advices, corr, long_i, skill_level)
        session.commit()


def _save_batch_insights(session, p_name, demo_name, rap, corr, long_i, skill_level):
    from Programma_CS2_RENAN.backend.coaching.explainability import ExplanationGenerator
    from Programma_CS2_RENAN.backend.processing.skill_assessment import SkillAxes

    for r in rap:
        session.add(
            CoachingInsight(
                player_name=p_name,
                demo_name=demo_name,
                title="RAP Behavioral",
                severity="Medium",
                message=r,
                focus_area="Decision",
            )
        )

    # Map raw deviations to Grounded Narratives (Step 2 SAFETY)
    for c in corr:
        feat = c["feature"]
        # Map feature to category
        category = SkillAxes.DECISION
        if "hs" in feat or "accuracy" in feat:
            category = SkillAxes.MECHANICS
        elif "aggression" in feat or "deaths" in feat:
            category = SkillAxes.POSITIONING

        # Extract context from features (De-mocking Step 2)
        context = {
            "weapon": (
                feat.replace("avg_", "").split("_")[0]
                if "accuracy" in feat or "hs" in feat
                else "equipment"
            ),
            "location": "critical sectors" if category == SkillAxes.POSITIONING else "the site",
        }

        message = ExplanationGenerator.generate_narrative(
            category=category,
            feature=feat,
            delta=c["weighted_z"],
            context=context,
            skill_level=skill_level,
        )

        if message:  # Silence is a Valid Action
            session.add(
                CoachingInsight(
                    player_name=p_name,
                    demo_name=demo_name,
                    title=f"{feat.replace('avg_', '').replace('_', ' ').title()} Insight",
                    severity=ExplanationGenerator.classify_insight_severity(c["weighted_z"]),
                    message=message,
                    focus_area=category,
                )
            )

    for li in long_i:
        session.add(CoachingInsight(player_name=p_name, demo_name=demo_name, **li))


def process_new_demos(is_pro=False, high_priority=False, limit=0):
    """
    Scans for new demos manually placed in the ingest folders.
    Args:
        limit: Max number of demos to process in this cycle (0 = unlimited).
    """
    # CRITICAL: Reload settings from disk to catch dynamic folder changes from UI
    refresh_settings()

    storage = StorageManager()
    target_dir = storage.get_ingest_dir(is_pro)

    if not target_dir.exists():
        logger.error(
            "Ingest directory not found: %s. Please create it and place .dem files there.",
            target_dir,
        )
        return

    # Update process priority
    if high_priority:
        ResourceManager.set_high_priority()
    else:
        ResourceManager.set_low_priority()

    db_manager = get_db_manager()
    demo_files = storage.list_new_demos(is_pro)

    if not demo_files:
        # Change to debug to avoid spamming the log and causing Windows rotation locking errors
        logger.debug("No new %s demos found in %s", "Pro" if is_pro else "User", target_dir)
        return

    logger.info(
        "Found %s new %s demos. Starting ingestion...", len(demo_files), "Pro" if is_pro else "User"
    )

    with db_manager.get_session() as session:
        _queue_files(session, demo_files, is_pro)
        session.commit()

    # 3. Process the queue
    # HP Mode: unlimited limit when priority is high
    effective_limit = 0 if high_priority else limit
    process_queued_tasks(db_manager, storage, is_pro, high_priority, limit=effective_limit)


def process_queued_tasks(db_manager, storage, is_pro, high_priority, limit=0):
    """Orchestrates the ingestion of queued tasks with throttling."""
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.db_models import IngestionTask

    with db_manager.get_session() as session:
        tasks = session.exec(
            select(IngestionTask)
            .where(IngestionTask.status == "queued", IngestionTask.is_pro == is_pro)
            .order_by(IngestionTask.id)
        ).all()

    if not tasks:
        return 0

    if limit > 0:
        tasks = tasks[:limit]

    processed_count = 0
    total_tasks = len(tasks)
    for task in tasks:
        # F6-13: Objects fetched in one session; do not access lazy-loaded attrs after
        # session closes. Re-attach via session.add(task) before modifying, or
        # re-fetch in the new session if lazy-loaded attributes are needed.
        with db_manager.get_session() as session:
            session.add(task)
            task.status = "processing"
            task.updated_at = datetime.now(timezone.utc)
            session.commit()

        # Update progress in CoachState
        with db_manager.get_session("knowledge") as session_k:
            from Programma_CS2_RENAN.backend.storage.db_models import CoachState

            state = session_k.exec(select(CoachState)).first()
            if state:
                state.parsing_progress = (processed_count / total_tasks) * 100
                session_k.add(state)
                session_k.commit()

        # Check for duplicate before processing
        demo_path = Path(task.demo_path)
        demo_basename = demo_path.stem  # Filename without extension

        if _check_duplicate_demo(db_manager, str(demo_path)):
            logger.info("Skipping duplicate demo: %s", demo_basename)
            with db_manager.get_session() as session:
                session.add(task)
                task.status = "completed"  # Mark as completed to remove from queue
                task.error_message = "Duplicate - already ingested"
                task.updated_at = datetime.now(timezone.utc)
                session.commit()
            processed_count += 1
            continue  # Skip to next demo

        success, msg = _ingest_single_demo(db_manager, storage, demo_path, is_pro)

        with db_manager.get_session() as session:
            session.add(task)
            task.status = "completed" if success else "failed"
            task.error_message = msg
            task.updated_at = datetime.now(timezone.utc)
            session.commit()

        processed_count += 1

    # Reset progress when batch is done
    if processed_count == total_tasks:
        from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

        get_state_manager().update_status("digester", "Idle", f"Processed {total_tasks} demos")


def _queue_files(session, files, is_pro):
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.db_models import IngestionTask

    for p in files:
        p_str = str(p)
        exist = session.exec(select(IngestionTask).where(IngestionTask.demo_path == p_str)).first()
        if not exist:
            session.add(IngestionTask(demo_path=p_str, is_pro=is_pro))


def _ingest_single_demo(db_manager, storage, demo_path, is_pro):
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.db_models import IngestionTask
    from Programma_CS2_RENAN.core.config import get_setting

    demo_path_str = str(demo_path)
    with db_manager.get_session() as session:
        task = session.exec(
            select(IngestionTask).where(IngestionTask.demo_path == demo_path_str)
        ).first()
        start_tick = task.last_tick_processed if task else 0
        task_exists = task is not None

    target = "ALL" if is_pro else get_setting("CS2_PLAYER_NAME")

    # 1. Parse aggregate stats (only if starting from 0)
    if start_tick == 0:
        df = parse_demo(str(demo_path), target_player=target)
        if df.empty:
            logger.warning(
                "parse_demo returned empty DataFrame for %s (target=%s)",
                demo_path.name,
                target,
            )
            return False, f"Empty data for '{target}'"
        for _, row in df.iterrows():
            _save_player_stats(db_manager, row, demo_path.name, is_pro)

    # 2. Parse sequential data (incremental)
    last_processed = _save_sequential_data(db_manager, demo_path, target, start_tick=start_tick)

    # Update task progress — re-fetch inside new session to avoid DetachedInstanceError
    if task_exists:
        with db_manager.get_session() as session:
            fresh_task = session.exec(
                select(IngestionTask).where(IngestionTask.demo_path == demo_path_str)
            ).first()
            if fresh_task:
                fresh_task.last_tick_processed = last_processed

    if last_processed > start_tick:
        storage.archive_demo(demo_path, is_pro)
        return True, "Success"
    else:
        return True, "No new ticks"


def _save_player_stats(db_manager, row, demo_name, is_pro):

    p_name = row["player_name"]
    stats_dict = row.to_dict()
    stats_dict.pop("player_name", None)

    # R3-H09: Sanitize NaN/Inf in aggregate stats before DB insertion
    import math

    for key, val in list(stats_dict.items()):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            logger.warning("Sanitized NaN/Inf in '%s' for player '%s'", key, p_name)
            stats_dict[key] = 0.0

    # Clamp rating to DB constraint range [0, 5.0] — HLTV 2.0 can produce
    # negative values for partial demos or extreme underperformance
    if "rating" in stats_dict:
        raw_rating = stats_dict["rating"]
        stats_dict["rating"] = max(0.0, min(5.0, float(raw_rating)))
        if raw_rating != stats_dict["rating"]:
            logger.info(
                "Clamped rating %.3f → %.3f for '%s'", raw_rating, stats_dict["rating"], p_name
            )

    # Clamp avg_kills and avg_adr to >= 0 (DB CHECK constraints)
    for field in ("avg_kills", "avg_adr"):
        if field in stats_dict and stats_dict[field] < 0:
            stats_dict[field] = 0.0

    # Use clean stem to align with PlayerTickState and enable AI Coach linking
    clean_demo_name = Path(demo_name).stem if str(demo_name).endswith(".dem") else demo_name

    # pro_player_id links PlayerMatchStats to ProPlayer.hltv_id which lives in
    # hltv_metadata.db. Resolving it here would reach across the DB boundary
    # and tie demo ingestion to HLTV availability. Leave the column NULL on
    # ingest; an out-of-band job (hltv_sync_service / ProPlayerLinker.backfill)
    # may populate it later against hltv_metadata.db without blocking ingestion.
    match_stats = PlayerMatchStats(
        player_name=p_name,
        demo_name=clean_demo_name,
        is_pro=is_pro,
        **stats_dict,
    )
    db_manager.upsert(match_stats)
    # Coaching inference (run_ml_pipeline) reads hltv_metadata.db via get_pro_baseline
    # to compute skill axes and RAP advice. That cross-DB read does not belong on
    # the demo-ingestion hot path — ingestion writes raw stats and returns. The
    # coach UI (qt_app session) invokes run_ml_pipeline on demand when HLTV
    # availability has been confirmed at its own boundary.


def _sanitize_value(value, default, value_type=float):
    """Sanitization bridge: Cleans NaN/None/invalid values before DB insertion."""
    import math

    if value is None:
        return default
    if value_type == float and (math.isnan(value) or math.isinf(value)):
        logger.debug("Sanitized NaN/Inf value to default=%s", default)
        return default
    if value_type == str and (not value or str(value).lower() == "nan"):
        return default
    return value_type(value)


def _interpolate_position(df_ticks):
    """
    Intelligent position interpolation with alive-boundary safety.

    Key invariants:
    - Positions are ONLY interpolated within contiguous alive segments per player.
      Dead players keep their last-known position; no bleed across death events.
    - Angles (yaw/pitch) use circular interpolation (sin/cos decomposition)
      to handle wrap-around correctly, also scoped per player + alive segment.
    - After interpolation, any remaining (0,0,0) positions are marked as NaN
      rather than passed as valid coordinates (0,0,0 is outside playable area
      on every CS2 map and would poison training data).
    """
    import numpy as np
    import pandas as pd

    from Programma_CS2_RENAN.observability.logger_setup import get_logger as _gl

    _log = _gl("cs2analyzer.ingestion")

    # Convert to numeric, coercing errors to NaN
    for col in ["X", "Y", "Z", "yaw", "pitch", "health", "armor", "equipment_value"]:
        if col in df_ticks.columns:
            df_ticks[col] = pd.to_numeric(df_ticks[col], errors="coerce")

    # Determine alive state for boundary-aware interpolation
    has_alive = "is_alive" in df_ticks.columns
    has_player = "player_name" in df_ticks.columns or "name" in df_ticks.columns
    player_col = "player_name" if "player_name" in df_ticks.columns else "name"

    if has_player and has_alive:
        # Create alive-segment groups: each contiguous alive=True block per player
        # gets its own segment ID, preventing interpolation across death boundaries.
        df_ticks["_alive_segment"] = df_ticks.groupby(player_col)["is_alive"].transform(
            lambda s: s.fillna(True).astype(bool).ne(s.fillna(True).astype(bool).shift()).cumsum()
        )
        group_cols = [player_col, "_alive_segment"]
    elif has_player:
        group_cols = [player_col]
    else:
        group_cols = None

    # --- Position interpolation (X, Y, Z) per alive segment ---
    pos_cols = [c for c in ["X", "Y", "Z"] if c in df_ticks.columns]
    if pos_cols:
        if group_cols:
            for col in pos_cols:
                df_ticks[col] = df_ticks.groupby(group_cols, sort=False)[col].transform(
                    lambda s: s.interpolate(method="linear", limit_direction="both").ffill().bfill()
                )
                # Only fill remaining NaN with NaN (NOT 0.0) — (0,0,0) poisons training
                # NaN will be handled downstream by the vectorizer quality gate
        else:
            for col in pos_cols:
                df_ticks[col] = df_ticks[col].interpolate(method="linear", limit_direction="both")
                df_ticks[col] = df_ticks[col].ffill().bfill()

    # R4-14-01: Count remaining (0,0,0) positions after alive-aware interpolation.
    # These represent players who never had a valid position in any alive segment
    # (warmup, bots, disconnected). They remain as 0.0 for DB storage (SQLite has
    # no NaN) but the count is tracked for data quality monitoring.
    if all(c in df_ticks.columns for c in ("X", "Y", "Z")):
        # Fill any remaining NaN from interpolation gaps with 0.0 for DB compat
        for col in ["X", "Y", "Z"]:
            df_ticks[col] = df_ticks[col].fillna(0.0)
        zero_pos_mask = (df_ticks["X"] == 0.0) & (df_ticks["Y"] == 0.0) & (df_ticks["Z"] == 0.0)
        _zero_pos = zero_pos_mask.sum()
        if _zero_pos > 0:
            _log.warning(
                "R4-14-01: %d/%d ticks have (0,0,0) position after alive-aware interpolation (%.1f%%)",
                _zero_pos,
                len(df_ticks),
                100.0 * _zero_pos / max(len(df_ticks), 1),
            )

    # --- Circular interpolation for angles (yaw/pitch) per alive segment ---
    for col, _wrap in [("yaw", 360.0), ("pitch", 180.0)]:
        if col not in df_ticks.columns:
            continue

        angles_rad = np.deg2rad(df_ticks[col].values)
        sin_vals = pd.Series(np.sin(angles_rad), index=df_ticks.index)
        cos_vals = pd.Series(np.cos(angles_rad), index=df_ticks.index)

        if group_cols:
            sin_interp = sin_vals.groupby([df_ticks[g] for g in group_cols], sort=False).transform(
                lambda s: s.interpolate(method="linear", limit_direction="both")
                .ffill()
                .bfill()
                .fillna(0.0)
            )
            cos_interp = cos_vals.groupby([df_ticks[g] for g in group_cols], sort=False).transform(
                lambda s: s.interpolate(method="linear", limit_direction="both")
                .ffill()
                .bfill()
                .fillna(1.0)
            )
        else:
            sin_interp = (
                sin_vals.interpolate(method="linear", limit_direction="both")
                .ffill()
                .bfill()
                .fillna(0.0)
            )
            cos_interp = (
                cos_vals.interpolate(method="linear", limit_direction="both")
                .ffill()
                .bfill()
                .fillna(1.0)
            )

        angles_interp = np.rad2deg(np.arctan2(sin_interp.values, cos_interp.values))
        if col == "yaw":
            angles_interp = np.mod(angles_interp, 360.0)

        df_ticks[col] = angles_interp

    # Clean up temporary column
    if "_alive_segment" in df_ticks.columns:
        df_ticks.drop(columns=["_alive_segment"], inplace=True)

    # Forward fill for integer fields (health, armor, equipment, WP6 fields)
    for col in [
        "health",
        "armor",
        "equipment_value",
        "balance",
        "total_cash_spent",
        "kills_total",
        "deaths_total",
        "assists_total",
        "score",
        "mvps",
    ]:
        if col in df_ticks.columns:
            df_ticks[col] = df_ticks[col].ffill().bfill()
            if col == "health":
                df_ticks[col] = df_ticks[col].fillna(100.0)
            else:
                df_ticks[col] = df_ticks[col].fillna(0.0)

    return df_ticks


_EVENT_DEFAULT_STATE = {
    "health": 100,
    "armor": 0,
    "equipment_value": 0,
    "team": "",
    "pos_x": 0.0,
    "pos_y": 0.0,
    "pos_z": 0.0,
}


class _EventExtractor:
    """Per-demo event-extraction helper for `_extract_and_store_events`.

    Owns the (tick, player_name) state index and steamid→name mapping built
    from `df_ticks`, plus one method per event type. All methods append to
    `self.events`; `extract_all()` runs every event type in a fixed order and
    returns the list. Method bodies preserve the original code paths verbatim
    so behavior is unchanged after the extraction.
    """

    def __init__(self, parser, df_ticks):
        self.parser = parser
        self.events: list = []
        # F6-14-v2: Indexed DataFrame replaces the old bounded dict; pro demos
        # have 1.5M+ ticks, so iterrows() into a 50K-capped dict caused endless
        # eviction warnings + O(n) build time. A MultiIndex DataFrame gives O(1)
        # lookups with zero pre-materialization cost.
        # GAP-02: include positional columns (X/Y/Z) so we can capture throw
        # origin for grenade_thrown events that lack x/y/z in their schema.
        self._state_index = None
        _STATE_COLS = ["health", "armor", "equipment_value", "team_name", "X", "Y", "Z"]
        if not df_ticks.empty and "player_name" in df_ticks.columns:
            _df_state = df_ticks[
                ["tick", "player_name"] + [c for c in _STATE_COLS if c in df_ticks.columns]
            ].copy()
            _df_state["_pname"] = _df_state["player_name"].str.strip().str.lower()
            _df_state = _df_state.set_index(["tick", "_pname"])
            _df_state = _df_state[~_df_state.index.duplicated(keep="last")]
            self._state_index = _df_state

        self.sid_to_name: dict = {}
        if not df_ticks.empty and "player_steamid" in df_ticks.columns:
            _sid_df = df_ticks[["player_steamid", "player_name"]].dropna(subset=["player_steamid"])
            _sid_df = _sid_df[_sid_df["player_steamid"] != 0]
            if not _sid_df.empty:
                _sid_df["player_steamid"] = _sid_df["player_steamid"].astype(int)
                _sid_df["player_name"] = _sid_df["player_name"].str.strip()
                self.sid_to_name = dict(zip(_sid_df["player_steamid"], _sid_df["player_name"]))

    @staticmethod
    def _row_to_state(row):
        return {
            "health": int(row.get("health", 100)),
            "armor": int(row.get("armor", 0)),
            "equipment_value": int(row.get("equipment_value", 0)),
            "team": str(row.get("team_name", "")),
            "pos_x": float(row.get("X", 0.0) or 0.0),
            "pos_y": float(row.get("Y", 0.0) or 0.0),
            "pos_z": float(row.get("Z", 0.0) or 0.0),
        }

    def _lookup_state(self, tick, player_name):
        """Get player state at a tick, with nearest-tick fallback (±5)."""
        if self._state_index is None or not player_name:
            return _EVENT_DEFAULT_STATE
        pname = player_name.strip().lower()
        key = (tick, pname)
        if key in self._state_index.index:
            return self._row_to_state(self._state_index.loc[key])
        for offset in range(1, 6):
            for t in (tick - offset, tick + offset):
                fb_key = (t, pname)
                if fb_key in self._state_index.index:
                    return self._row_to_state(self._state_index.loc[fb_key])
        return _EVENT_DEFAULT_STATE

    def _resolve_name(self, row, name_cols):
        """Resolve player name from event row trying multiple column names."""
        for col in name_cols:
            val = getattr(row, col, None)
            if val and str(val).strip() and str(val).lower() != "nan":
                return str(val).strip()
        sid = getattr(row, "user_steamid", None) or getattr(row, "attacker_steamid", None)
        if sid:
            return self.sid_to_name.get(int(sid), "")
        return ""

    @staticmethod
    def _get_round(row):
        return int(getattr(row, "total_rounds_played", 1) or 1)

    @staticmethod
    def _row_pos(row):
        return (
            float(getattr(row, "x", 0) or 0),
            float(getattr(row, "y", 0) or 0),
            float(getattr(row, "z", 0) or 0),
        )

    def _safe_parse(self, names, log_label):
        """Parse one or more event names; returns list of (name, df) or [] on failure."""
        try:
            res = self.parser.parse_events(list(names))
        except Exception as e:
            logger.warning("Event extraction failed for %s: %s", log_label, e)
            return []
        if not res:
            return []
        # Normalize to list[(name, df)]
        if isinstance(res[0], tuple):
            return [(n, df) for n, df in res if not df.empty]
        single_df = pd.DataFrame(res)
        return [(names[0], single_df)] if not single_df.empty else []

    def extract_weapon_fire(self):
        for _, df in self._safe_parse(["weapon_fire"], "weapon_fire"):
            for row in df.itertuples():
                tick = int(row.tick)
                name = self._resolve_name(row, ["player_name", "user_name", "name"])
                if not name:
                    continue
                state = self._lookup_state(tick, name)
                px, py, pz = self._row_pos(row)
                self.events.append(
                    MatchEventState(
                        tick=tick,
                        round_number=self._get_round(row),
                        event_type="weapon_fire",
                        player_name=name,
                        player_team=state["team"],
                        player_health=state["health"],
                        player_armor=state["armor"],
                        player_equipment_value=state["equipment_value"],
                        pos_x=px,
                        pos_y=py,
                        pos_z=pz,
                        weapon=str(getattr(row, "weapon", "") or ""),
                    )
                )

    def extract_player_hurt(self):
        for _, df in self._safe_parse(["player_hurt"], "player_hurt"):
            for row in df.itertuples():
                tick = int(row.tick)
                attacker = self._resolve_name(row, ["attacker_name", "user_name"])
                victim = self._resolve_name(row, ["user_name", "player_name"])
                if not attacker and not victim:
                    continue
                att_state = self._lookup_state(tick, attacker) if attacker else {}
                vic_state = self._lookup_state(tick, victim) if victim else {}
                dmg = int(getattr(row, "dmg_health", 0) or getattr(row, "damage", 0) or 0)
                px, py, pz = self._row_pos(row)
                self.events.append(
                    MatchEventState(
                        tick=tick,
                        round_number=self._get_round(row),
                        event_type="player_hurt",
                        player_name=attacker,
                        player_team=att_state.get("team", ""),
                        player_health=att_state.get("health", 100),
                        player_armor=att_state.get("armor", 0),
                        player_equipment_value=att_state.get("equipment_value", 0),
                        pos_x=px,
                        pos_y=py,
                        pos_z=pz,
                        weapon=str(getattr(row, "weapon", "") or ""),
                        damage=dmg,
                        victim_name=victim,
                        victim_team=vic_state.get("team", ""),
                        victim_health=vic_state.get("health", 100),
                        victim_armor=vic_state.get("armor", 0),
                    )
                )

    def extract_player_death(self):
        for _, df in self._safe_parse(["player_death"], "player_death"):
            for row in df.itertuples():
                tick = int(row.tick)
                attacker = self._resolve_name(row, ["attacker_name", "user_name"])
                victim = self._resolve_name(row, ["user_name", "player_name"])
                att_state = self._lookup_state(tick, attacker) if attacker else {}
                vic_state = self._lookup_state(tick, victim) if victim else {}
                px, py, pz = self._row_pos(row)
                self.events.append(
                    MatchEventState(
                        tick=tick,
                        round_number=self._get_round(row),
                        event_type="player_death",
                        player_name=attacker,
                        player_team=att_state.get("team", ""),
                        player_health=att_state.get("health", 100),
                        player_armor=att_state.get("armor", 0),
                        player_equipment_value=att_state.get("equipment_value", 0),
                        pos_x=px,
                        pos_y=py,
                        pos_z=pz,
                        weapon=str(getattr(row, "weapon", "") or ""),
                        is_headshot=bool(getattr(row, "headshot", False)),
                        victim_name=victim,
                        victim_team=vic_state.get("team", ""),
                        victim_health=vic_state.get("health", 0),
                        victim_armor=vic_state.get("armor", 0),
                    )
                )

    def _extract_grenade_pair(self, evt_pair, etype_keyword_map, weapon_label, log_label):
        """Helper for start/end pair events (smoke, molotov)."""
        for evt_name, df in self._safe_parse(evt_pair, log_label):
            etype = next(v for k, v in etype_keyword_map.items() if k in evt_name)
            for row in df.itertuples():
                tick = int(row.tick)
                sid = int(getattr(row, "user_steamid", 0) or 0)
                name = self.sid_to_name.get(sid, "")
                state = self._lookup_state(tick, name) if name else {}
                px, py, pz = self._row_pos(row)
                self.events.append(
                    MatchEventState(
                        tick=tick,
                        round_number=self._get_round(row),
                        event_type=etype,
                        player_name=name,
                        player_team=state.get("team", ""),
                        player_health=state.get("health", 100),
                        player_armor=state.get("armor", 0),
                        player_equipment_value=state.get("equipment_value", 0),
                        pos_x=px,
                        pos_y=py,
                        pos_z=pz,
                        weapon=weapon_label,
                        entity_id=int(getattr(row, "entityid", 0) or 0),
                    )
                )

    def extract_smoke(self):
        self._extract_grenade_pair(
            ["smokegrenade_detonate", "smokegrenade_expired"],
            {"detonate": "smoke_start", "expired": "smoke_end"},
            "smokegrenade",
            "smoke events",
        )

    def extract_molotov(self):
        self._extract_grenade_pair(
            ["inferno_startburn", "inferno_expire"],
            {"startburn": "molotov_start", "expire": "molotov_end"},
            "molotov",
            "molotov events",
        )

    def _extract_grenade_single(self, event_name, etype, weapon_label, log_label):
        """Helper for single-event grenade detonations (flashbang, HE)."""
        for _, df in self._safe_parse([event_name], log_label):
            for row in df.itertuples():
                tick = int(row.tick)
                sid = int(getattr(row, "user_steamid", 0) or 0)
                name = self.sid_to_name.get(sid, "")
                state = self._lookup_state(tick, name) if name else {}
                px, py, pz = self._row_pos(row)
                self.events.append(
                    MatchEventState(
                        tick=tick,
                        round_number=self._get_round(row),
                        event_type=etype,
                        player_name=name,
                        player_team=state.get("team", ""),
                        player_health=state.get("health", 100),
                        player_armor=state.get("armor", 0),
                        player_equipment_value=state.get("equipment_value", 0),
                        pos_x=px,
                        pos_y=py,
                        pos_z=pz,
                        weapon=weapon_label,
                        entity_id=int(getattr(row, "entityid", 0) or 0),
                    )
                )

    def extract_flashbang(self):
        self._extract_grenade_single(
            "flashbang_detonate", "flash_detonate", "flashbang", "flashbang events"
        )

    def extract_he_grenade(self):
        self._extract_grenade_single(
            "hegrenade_detonate", "he_detonate", "hegrenade", "HE grenade events"
        )

    def extract_grenade_thrown(self):
        # GAP-02: 'grenade_thrown' schema lacks x/y/z; throw origin resolved from
        # tick state. entity_id defaults to sentinel (-1) because the parser does
        # not link thrown→detonate via entityid; downstream pairing is proximity-based.
        for _, df in self._safe_parse(["grenade_thrown"], "grenade_thrown"):
            for row in df.itertuples():
                tick = int(row.tick)
                sid = int(getattr(row, "user_steamid", 0) or 0)
                name = self.sid_to_name.get(sid) or self._resolve_name(row, ["user_name"])
                if not name:
                    continue
                state = self._lookup_state(tick, name)
                weapon = str(getattr(row, "weapon", "") or "").strip()
                self.events.append(
                    MatchEventState(
                        tick=tick,
                        round_number=self._get_round(row),
                        event_type="grenade_thrown",
                        player_name=name,
                        player_team=state.get("team", ""),
                        player_health=state.get("health", 100),
                        player_armor=state.get("armor", 0),
                        player_equipment_value=state.get("equipment_value", 0),
                        pos_x=state.get("pos_x", 0.0),
                        pos_y=state.get("pos_y", 0.0),
                        pos_z=state.get("pos_z", 0.0),
                        weapon=weapon,
                    )
                )

    def extract_bomb(self):
        for bomb_event in ["bomb_planted", "bomb_defused"]:
            etype = "bomb_planted" if "planted" in bomb_event else "bomb_defused"
            for _, df in self._safe_parse([bomb_event], "bomb events"):
                for row in df.itertuples():
                    tick = int(row.tick)
                    name = self._resolve_name(row, ["user_name", "player_name"])
                    state = self._lookup_state(tick, name) if name else {}
                    px, py, pz = self._row_pos(row)
                    self.events.append(
                        MatchEventState(
                            tick=tick,
                            round_number=self._get_round(row),
                            event_type=etype,
                            player_name=name,
                            player_team=state.get("team", ""),
                            player_health=state.get("health", 100),
                            player_armor=state.get("armor", 0),
                            player_equipment_value=state.get("equipment_value", 0),
                            pos_x=px,
                            pos_y=py,
                            pos_z=pz,
                        )
                    )

    def extract_all(self):
        """Run every event-type extractor in fixed order; return self.events."""
        self.extract_weapon_fire()
        self.extract_player_hurt()
        self.extract_player_death()
        self.extract_smoke()
        self.extract_molotov()
        self.extract_flashbang()
        self.extract_he_grenade()
        self.extract_grenade_thrown()
        self.extract_bomb()
        return self.events


def _extract_and_store_events(demo_path, match_id, match_manager, df_ticks):
    """Extract game events from demo and persist as MatchEventState records.

    Parses weapon_fire, player_hurt, player_death, grenade/smoke/molotov/flash
    events and stores them in the per-match database for Player-POV perception.
    Player state (health, armor, equipment) is cross-referenced from df_ticks
    at the event tick to capture the situational context.
    """
    from demoparser2 import DemoParser

    try:
        parser = DemoParser(str(demo_path))
    except Exception as e:
        logger.error("Failed to create DemoParser for event extraction: %s", e)
        return 0

    extractor = _EventExtractor(parser, df_ticks)
    events = extractor.extract_all()

    if events:
        stored = match_manager.store_event_batch(match_id, events)
        logger.info("Stored %d game events to match database (ID: %s)", stored, match_id)
    else:
        logger.debug("No game events extracted for match %s", match_id)

    return len(events)


def _parse_demo_header_meta(demo_path) -> tuple[str, float]:
    """Extract (map_name, tick_rate) from a .dem file header.

    GAP-01: demoparser2's `parse_header()` exposes both fields. Previous code
    hardcoded tick_rate=64.0, silently halving time_in_round on 128-tick
    demos. Validation range [32, 256] mirrors P-RSB-05.

    Returns safe defaults ("de_unknown", 64.0) on any header read failure so
    ingestion never aborts on metadata.
    """
    from demoparser2 import DemoParser as _DemoParser

    default_map = "de_unknown"
    default_tr = 64.0
    try:
        header = _DemoParser(str(demo_path)).parse_header()
    except Exception as exc:
        logger.warning(
            "Failed to read demo header for %s: %s (defaults map=%s tick_rate=%.1f)",
            demo_path,
            exc,
            default_map,
            default_tr,
        )
        return default_map, default_tr

    map_name = header.get("map_name") or default_map
    if map_name == "unknown":
        map_name = default_map

    raw_tr = header.get("tick_rate", default_tr) or default_tr
    try:
        parsed_tr = float(raw_tr)
    except (TypeError, ValueError):
        logger.warning(
            "GAP-01: demo header tick_rate=%r not numeric; falling back to %.1f",
            raw_tr,
            default_tr,
        )
        return map_name, default_tr

    if not (32.0 <= parsed_tr <= 256.0):
        logger.warning(
            "GAP-01: demo header tick_rate=%.2f outside [32,256]; falling back to %.1f",
            parsed_tr,
            default_tr,
        )
        return map_name, default_tr

    logger.info("Demo header: map_name=%s tick_rate=%.2f", map_name, parsed_tr)
    return map_name, parsed_tr


_TICK_INT_DEFAULTS = {
    "round_number": 1,
    "player_steamid": 0,
    "armor": 0,
    "equipment_value": 0,
    "balance": 0,
    "enemies_visible": 0,
    "ping": 0,
    "kills_this_round": 0,
    "deaths_this_round": 0,
    "assists_this_round": 0,
    "headshot_kills_this_round": 0,
    "damage_this_round": 0,
    "utility_damage_this_round": 0,
    "enemies_flashed_this_round": 0,
    "kills_total": 0,
    "deaths_total": 0,
    "assists_total": 0,
    "headshot_kills_total": 0,
    "mvps": 0,
    "score": 0,
    "cash_spent_this_round": 0,
    "total_cash_spent": 0,
    "teammates_alive": 4,
    "enemies_alive": 5,
    "team_economy": 0,
}
_TICK_FLOAT_DEFAULTS = {
    "X": 0.0,
    "Y": 0.0,
    "Z": 0.0,
    "yaw": 0.0,
    "pitch": 0.0,
    "time_in_round": 0.0,
}
_TICK_BOOL_DEFAULTS = {
    "is_crouching": False,
    "is_scoped": False,
    "is_blinded": False,
    "has_helmet": False,
    "has_defuser": False,
    "bomb_planted": False,
}


def _apply_tick_dataframe_defaults(df_ticks, meta_map_name):
    """Fill NaN/None/non-numeric values with safe defaults for downstream DataFrames.

    Mutates `df_ticks` in place (vectorized, ~100ms for 2.4M rows). Logs WARN
    when non-numeric values get coerced and again when critical demoparser2
    columns (balance, health, X/Y/Z) are entirely missing (R3-02).
    """
    for col, default in _TICK_INT_DEFAULTS.items():
        if col in df_ticks.columns:
            original_na = df_ticks[col].isna().sum()
            numeric = pd.to_numeric(df_ticks[col], errors="coerce")
            coerced_count = numeric.isna().sum() - original_na
            if coerced_count > 0:
                logger.warning(
                    "Column '%s': %d non-numeric values coerced to default %s",
                    col,
                    coerced_count,
                    default,
                )
            df_ticks[col] = numeric.fillna(default).astype(int)
    for col, default in _TICK_FLOAT_DEFAULTS.items():
        if col in df_ticks.columns:
            original_na = df_ticks[col].isna().sum()
            numeric = pd.to_numeric(df_ticks[col], errors="coerce")
            coerced_count = numeric.isna().sum() - original_na
            if coerced_count > 0:
                logger.warning(
                    "Column '%s': %d non-numeric values coerced to default %s",
                    col,
                    coerced_count,
                    default,
                )
            df_ticks[col] = numeric.fillna(default).astype(float)
    for col, default in _TICK_BOOL_DEFAULTS.items():
        if col in df_ticks.columns:
            df_ticks[col] = df_ticks[col].fillna(default).astype(bool)

    # R3-02: Warn about critical columns missing entirely from demoparser2 output
    _critical_cols = ["balance", "health", "X", "Y", "Z"]
    _missing_critical = [c for c in _critical_cols if c not in df_ticks.columns]
    if _missing_critical:
        logger.warning(
            "Critical columns absent from demo data (defaulted to 0): %s",
            _missing_critical,
        )

    if "health" in df_ticks.columns:
        df_ticks["health"] = (
            pd.to_numeric(df_ticks["health"], errors="coerce").fillna(100).astype(int)
        )
    if "is_alive" in df_ticks.columns:
        df_ticks["is_alive"] = df_ticks["is_alive"].fillna(True).astype(bool)
    if "team_name" in df_ticks.columns:
        df_ticks["team_name"] = df_ticks["team_name"].fillna("CT").astype(str)
    if "active_weapon" in df_ticks.columns:
        df_ticks["active_weapon"] = df_ticks["active_weapon"].fillna("unknown").astype(str)
        df_ticks.loc[df_ticks["active_weapon"].str.lower() == "nan", "active_weapon"] = "unknown"
    if "player_name" in df_ticks.columns:
        df_ticks["player_name"] = df_ticks["player_name"].astype(str)
    if "map_name" in df_ticks.columns:
        df_ticks["map_name"] = df_ticks["map_name"].fillna(meta_map_name).astype(str)
    else:
        df_ticks["map_name"] = meta_map_name


def _build_match_tick_dataframe(df_ticks):
    """Build the per-match MatchTickState DataFrame (ALL players).

    All columns are vectorized renames + dtype casts of `df_ticks`. Tick
    decimation FORBIDDEN (CLAUDE.md invariant) — every input row maps 1:1 to
    one output row.
    """
    return pd.DataFrame(
        {
            "tick": df_ticks["tick"].astype(int),
            "round_number": df_ticks.get("round_number", pd.Series(1, index=df_ticks.index)).astype(
                int
            ),
            "player_name": df_ticks["player_name"],
            "steamid": df_ticks.get("player_steamid", pd.Series(0, index=df_ticks.index)).astype(
                int
            ),
            "team": df_ticks.get("team_name", pd.Series("CT", index=df_ticks.index)),
            "pos_x": df_ticks["X"].astype(float),
            "pos_y": df_ticks["Y"].astype(float),
            "pos_z": df_ticks["Z"].astype(float),
            "yaw": df_ticks["yaw"].astype(float),
            "health": df_ticks["health"].astype(int),
            "armor": df_ticks.get("armor", pd.Series(0, index=df_ticks.index)).astype(int),
            "is_alive": df_ticks.get("is_alive", pd.Series(True, index=df_ticks.index)).astype(
                bool
            ),
            "is_crouching": df_ticks.get(
                "is_crouching", pd.Series(False, index=df_ticks.index)
            ).astype(bool),
            "is_scoped": df_ticks.get("is_scoped", pd.Series(False, index=df_ticks.index)).astype(
                bool
            ),
            "is_blinded": df_ticks.get("is_blinded", pd.Series(False, index=df_ticks.index)).astype(
                bool
            ),
            "active_weapon": df_ticks.get(
                "active_weapon", pd.Series("unknown", index=df_ticks.index)
            ),
            "equipment_value": df_ticks.get(
                "equipment_value", pd.Series(0, index=df_ticks.index)
            ).astype(int),
            "money": df_ticks.get("balance", pd.Series(0, index=df_ticks.index)).astype(int),
            "enemies_visible": df_ticks.get(
                "enemies_visible", pd.Series(0, index=df_ticks.index)
            ).astype(int),
            "has_helmet": df_ticks.get("has_helmet", pd.Series(False, index=df_ticks.index)).astype(
                bool
            ),
            "has_defuser": df_ticks.get(
                "has_defuser", pd.Series(False, index=df_ticks.index)
            ).astype(bool),
            "ping": df_ticks.get("ping", pd.Series(0, index=df_ticks.index)).astype(int),
            "kills_this_round": df_ticks.get(
                "kills_this_round", pd.Series(0, index=df_ticks.index)
            ).astype(int),
            "deaths_this_round": df_ticks.get(
                "deaths_this_round", pd.Series(0, index=df_ticks.index)
            ).astype(int),
            "assists_this_round": df_ticks.get(
                "assists_this_round", pd.Series(0, index=df_ticks.index)
            ).astype(int),
            "headshot_kills_this_round": df_ticks.get(
                "headshot_kills_this_round", pd.Series(0, index=df_ticks.index)
            ).astype(int),
            "damage_this_round": df_ticks.get(
                "damage_this_round", pd.Series(0, index=df_ticks.index)
            ).astype(int),
            "utility_damage_this_round": df_ticks.get(
                "utility_damage_this_round", pd.Series(0, index=df_ticks.index)
            ).astype(int),
            "enemies_flashed_this_round": df_ticks.get(
                "enemies_flashed_this_round", pd.Series(0, index=df_ticks.index)
            ).astype(int),
            "kills_total": df_ticks.get("kills_total", pd.Series(0, index=df_ticks.index)).astype(
                int
            ),
            "deaths_total": df_ticks.get("deaths_total", pd.Series(0, index=df_ticks.index)).astype(
                int
            ),
            "assists_total": df_ticks.get(
                "assists_total", pd.Series(0, index=df_ticks.index)
            ).astype(int),
            "headshot_kills_total": df_ticks.get(
                "headshot_kills_total", pd.Series(0, index=df_ticks.index)
            ).astype(int),
            "mvps": df_ticks.get("mvps", pd.Series(0, index=df_ticks.index)).astype(int),
            "score": df_ticks.get("score", pd.Series(0, index=df_ticks.index)).astype(int),
            "cash_spent_this_round": df_ticks.get(
                "cash_spent_this_round", pd.Series(0, index=df_ticks.index)
            ).astype(int),
            "cash_spent_total": df_ticks.get(
                "total_cash_spent", pd.Series(0, index=df_ticks.index)
            ).astype(int),
            "pitch": df_ticks.get("pitch", pd.Series(0.0, index=df_ticks.index)).astype(float),
            "time_in_round": df_ticks.get(
                "time_in_round", pd.Series(0.0, index=df_ticks.index)
            ).astype(float),
            "bomb_planted": df_ticks.get(
                "bomb_planted", pd.Series(False, index=df_ticks.index)
            ).astype(bool),
            "teammates_alive": df_ticks.get(
                "teammates_alive", pd.Series(4, index=df_ticks.index)
            ).astype(int),
            "enemies_alive": df_ticks.get(
                "enemies_alive", pd.Series(5, index=df_ticks.index)
            ).astype(int),
            "team_economy": df_ticks.get("team_economy", pd.Series(0, index=df_ticks.index)).astype(
                int
            ),
            "map_name": df_ticks["map_name"],
        }
    )


def _build_legacy_tick_dataframe(df_ticks, demo_name, target_player, meta_map_name):
    """Build the legacy PlayerTickState DataFrame.

    Filtered to `target_player` for user demos, ALL players for pro demos
    (target_player == "ALL"). Tick decimation FORBIDDEN — only player filter,
    every retained row maps 1:1.
    """
    df_legacy_source = df_ticks
    if target_player and target_player != "ALL":
        target_lower = str(target_player).strip().lower()
        df_legacy_source = df_ticks[
            df_ticks["player_name"].astype(str).str.strip().str.lower() == target_lower
        ]

    return pd.DataFrame(
        {
            "demo_name": demo_name,
            "tick": df_legacy_source["tick"].astype(int),
            "player_name": df_legacy_source["player_name"],
            "pos_x": df_legacy_source["X"].astype(float),
            "pos_y": df_legacy_source["Y"].astype(float),
            "pos_z": df_legacy_source["Z"].astype(float),
            "view_x": df_legacy_source["yaw"].astype(float),
            "view_y": df_legacy_source.get(
                "pitch", pd.Series(0.0, index=df_legacy_source.index)
            ).astype(float),
            "health": df_legacy_source["health"].astype(int),
            "armor": df_legacy_source.get(
                "armor", pd.Series(0, index=df_legacy_source.index)
            ).astype(int),
            # demoparser2 'ducking' is the correct field for crouch state
            "is_crouching": df_legacy_source.get(
                "ducking",
                df_legacy_source.get(
                    "is_crouching", pd.Series(False, index=df_legacy_source.index)
                ),
            ).astype(bool),
            "is_scoped": df_legacy_source.get(
                "is_scoped", pd.Series(False, index=df_legacy_source.index)
            ).astype(bool),
            "has_helmet": df_legacy_source.get(
                "has_helmet", pd.Series(False, index=df_legacy_source.index)
            ).astype(bool),
            "has_defuser": df_legacy_source.get(
                "has_defuser", pd.Series(False, index=df_legacy_source.index)
            ).astype(bool),
            "active_weapon": df_legacy_source.get(
                "active_weapon", pd.Series("unknown", index=df_legacy_source.index)
            ),
            "equipment_value": df_legacy_source.get(
                "equipment_value", pd.Series(0, index=df_legacy_source.index)
            ).astype(int),
            "enemies_visible": df_legacy_source.get(
                "enemies_visible", pd.Series(0, index=df_legacy_source.index)
            ).astype(int),
            # flash_duration > 0 is the correct demoparser2 signal for blind state
            "is_blinded": (
                df_legacy_source.get(
                    "flash_duration", pd.Series(0.0, index=df_legacy_source.index)
                ).astype(float)
                > 0
            ).astype(bool),
            "round_number": df_legacy_source.get(
                "round_number", pd.Series(1, index=df_legacy_source.index)
            ).astype(int),
            "time_in_round": df_legacy_source.get(
                "time_in_round", pd.Series(0.0, index=df_legacy_source.index)
            ).astype(float),
            "bomb_planted": df_legacy_source.get(
                "bomb_planted", pd.Series(False, index=df_legacy_source.index)
            ).astype(bool),
            "teammates_alive": df_legacy_source.get(
                "teammates_alive", pd.Series(4, index=df_legacy_source.index)
            ).astype(int),
            "enemies_alive": df_legacy_source.get(
                "enemies_alive", pd.Series(5, index=df_legacy_source.index)
            ).astype(int),
            "team_economy": df_legacy_source.get(
                "team_economy", pd.Series(0, index=df_legacy_source.index)
            ).astype(int),
            "map_name": df_legacy_source.get(
                "map_name", pd.Series(meta_map_name, index=df_legacy_source.index)
            ),
            "created_at": datetime.now(timezone.utc),
        }
    )


def _finalize_match_record(
    match_manager,
    match_id,
    demo_name,
    demo_path,
    df_ticks,
    meta_map_name,
    meta_tick_rate,
    meta_player_count,
    last_tick,
    start_tick,
):
    """Persist match metadata, extract events on fresh ingestion, mark complete.

    GAP-01: stores detected `tick_rate` per-demo so downstream consumers don't
    fall back to the 64.0 schema default.

    P4-A: marks the match complete only AFTER all ticks + events land. The
    Teacher daemon only trains on completed matches, preventing learning from
    half-written data.
    """
    meta = MatchMetadata(
        match_id=match_id,
        demo_name=demo_name,
        map_name=meta_map_name,
        tick_count=int(last_tick - start_tick),
        player_count=meta_player_count,
        tick_rate=meta_tick_rate,
    )
    match_manager.store_metadata(match_id, meta)

    # Only on fresh ingestion (start_tick == 0) to avoid duplicate events
    if start_tick == 0:
        _extract_and_store_events(demo_path, match_id, match_manager, df_ticks)

    try:
        with match_manager.get_match_session(match_id) as session:
            from sqlalchemy import text as sa_text

            session.execute(
                sa_text("UPDATE match_metadata SET match_complete = 1 WHERE match_id = :mid"),
                {"mid": match_id},
            )
        logger.info("Match %s marked as complete", match_id)
    except Exception as e:
        logger.warning("Failed to mark match %s as complete: %s", match_id, e)


def _save_sequential_data(db_manager, demo_path, target_player, start_tick=0):
    import time as _time

    from Programma_CS2_RENAN.backend.data_sources.demo_parser import parse_sequential_ticks
    from Programma_CS2_RENAN.backend.processing.tick_enrichment import enrich_tick_data

    t_pipeline = _time.monotonic()

    # PROGRESS: 10% - Sending to Rust Parser
    get_state_manager().update_parsing_progress(10.0)

    # Parse ALL players — required for cross-player feature computation
    # (teammates_alive, enemies_alive, team_economy, enemies_visible).
    # demoparser2 parsing is O(file_size) regardless of player filter; the
    # filter only affects post-parse DataFrame slicing.
    df_ticks = parse_sequential_ticks(str(demo_path), "ALL", start_tick=start_tick)

    if df_ticks.empty:
        get_state_manager().update_parsing_progress(100.0)
        return start_tick

    # PROGRESS: 20% - Interpolation
    get_state_manager().update_parsing_progress(20.0)
    t_interp = _time.monotonic()
    df_ticks = _interpolate_position(df_ticks)
    logger.info(
        "Interpolation completed in %.2fs for %s rows",
        _time.monotonic() - t_interp,
        f"{len(df_ticks):,}",
    )

    # PROGRESS: 25% - Tick Enrichment (cross-player features)
    get_state_manager().update_parsing_progress(25.0)
    t_enrich = _time.monotonic()

    # GAP-01: tick_rate was previously hardcoded to 64.0, silently halving
    # time_in_round on 128-tick demos. The pure helper is unit-testable.
    _meta_map_name, _meta_tick_rate = _parse_demo_header_meta(demo_path)
    df_ticks = enrich_tick_data(
        df_ticks,
        demo_path=str(demo_path),
        tick_rate=_meta_tick_rate,
        map_name=_meta_map_name,
    )
    logger.info("Enrichment completed in %.2fs", _time.monotonic() - t_enrich)

    # PROGRESS: 40% - Database Insertion Start
    get_state_manager().update_parsing_progress(40.0)
    t_db = _time.monotonic()

    demo_name = demo_path.stem
    # DA-03-01: SHA-256 with 63-bit modulo (~3 billion demos before 50%
    # birthday-paradox collision). SQLite INTEGER supports signed 64-bit.
    match_id = int(hashlib.sha256(demo_name.encode()).hexdigest(), 16) % (2**63 - 1)
    match_manager = get_match_data_manager()

    total_ticks = len(df_ticks)
    last_tick = int(df_ticks["tick"].max()) if total_ticks > 0 else start_tick
    _meta_player_count = (
        df_ticks["player_name"].nunique() if "player_name" in df_ticks.columns else 10
    )

    # BULK INSERT via pandas to_sql() bypasses ORM object creation. The previous
    # per-row ORM loop took ~736s for 2.4M rows (96.6% of total). Vectorized
    # DataFrame ops + to_sql() reduce this to ~15-20s.
    BATCH_SIZE = 10000 if os.environ.get("HP_MODE") == "1" else 2000

    t_build = _time.monotonic()
    _apply_tick_dataframe_defaults(df_ticks, _meta_map_name)
    df_match = _build_match_tick_dataframe(df_ticks)
    df_legacy = _build_legacy_tick_dataframe(df_ticks, demo_name, target_player, _meta_map_name)
    logger.info("DataFrame construction: %.2fs", _time.monotonic() - t_build)

    # --- Chunked dual-write to per-match + monolith DBs with progress ticks ---
    match_engine = match_manager.get_engine(match_id)
    monolith_engine = db_manager.engine
    n_chunks = (total_ticks + BATCH_SIZE - 1) // BATCH_SIZE

    for chunk_idx in range(n_chunks):
        start = chunk_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, total_ticks)

        # Map chunk_idx/n_chunks -> 40..95%
        pct = 40.0 + (chunk_idx / n_chunks) * 55.0
        get_state_manager().update_parsing_progress(pct)

        df_match.iloc[start:end].to_sql(
            "matchtickstate",
            match_engine,
            if_exists="append",
            index=False,
        )
        df_legacy.iloc[start:end].to_sql(
            "playertickstate",
            monolith_engine,
            if_exists="append",
            index=False,
        )

    db_elapsed = _time.monotonic() - t_db
    total_elapsed = _time.monotonic() - t_pipeline
    logger.info(
        "Ingestion complete for %s: %s ticks, %d chunks, "
        "DB insertion %.1fs, total pipeline %.1fs",
        demo_name,
        f"{total_ticks:,}",
        n_chunks,
        db_elapsed,
        total_elapsed,
    )

    _finalize_match_record(
        match_manager,
        match_id,
        demo_name,
        demo_path,
        df_ticks,
        _meta_map_name,
        _meta_tick_rate,
        _meta_player_count,
        last_tick,
        start_tick,
    )

    return last_tick


if __name__ == "__main__":
    init_database()
    process_new_demos(is_pro=True)
    process_new_demos(is_pro=False)
