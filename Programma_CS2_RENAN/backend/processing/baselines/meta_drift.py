"""
Meta-Drift Surveillance Engine

Tracks shifts in professional playstyles over time.
If pros start playing differently, the Coach adjusts its certainty.
"""

from datetime import datetime, timedelta, timezone

import numpy as np
from sqlmodel import col, func, select

from Programma_CS2_RENAN.backend.storage.database import get_db_manager, get_hltv_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import (
    MATCH_STATS_DEMO_SUFFIX_RE,
    PlayerMatchStats,
    PlayerTickState,
    ProPlayerStatCard,
)


class MetaDriftEngine:
    """
    Analyzes the 'Knowledge Freshness' of the Pro Baseline.
    """

    @staticmethod
    def calculate_spatial_drift(map_name: str) -> float:
        """
        Implementation of Pillar 2 - Phase 3 (100%): Meta-Drift Surveillance.
        Compares pro positions in the last 30 days vs historical pro positions.
        """
        db = get_db_manager()
        limit_date = datetime.now(timezone.utc) - timedelta(days=30)

        with db.get_session() as s:
            # R4 HIGH (2026-07-16): the old query joined
            # PlayerTickState.match_id == PlayerMatchStats.id — unrelated ID
            # spaces (match_id references matchresult.match_id), pairing ticks
            # with essentially random stats rows; it also never filtered by
            # map, so the "drift on <map>" mixed every ingested map. Fixed by
            # attributing ticks through demo_name (WR-76 suffix stripped) and
            # filtering on PlayerTickState.map_name.
            pro_stats = s.exec(
                select(PlayerMatchStats.demo_name, PlayerMatchStats.processed_at).where(
                    PlayerMatchStats.is_pro == True  # noqa: E712
                )
            ).all()
            if not pro_stats:
                return 0.0

            recent_demos = set()
            hist_demos = set()
            for demo_name, processed_at in pro_stats:
                if not demo_name or processed_at is None:
                    continue
                # SQLite drops tzinfo on round-trip; stored values are UTC by
                # convention (default_factory=datetime.now(timezone.utc)).
                if processed_at.tzinfo is None:
                    processed_at = processed_at.replace(tzinfo=timezone.utc)
                stem = MATCH_STATS_DEMO_SUFFIX_RE.sub("", demo_name)
                if processed_at >= limit_date:
                    recent_demos.add(stem)
                else:
                    hist_demos.add(stem)
            # A demo re-processed recently must not count as historical too.
            hist_demos -= recent_demos
            if not recent_demos or not hist_demos:
                return 0.0

            def _positions(demo_names):
                stmt = (
                    select(PlayerTickState.pos_x, PlayerTickState.pos_y)
                    .where(col(PlayerTickState.demo_name).in_(sorted(demo_names)))
                    .where(PlayerTickState.map_name == map_name)
                    .where(PlayerTickState.tick % 128 == 0)
                    .limit(50_000)
                )
                return s.exec(stmt).all()

            recent_pts = _positions(recent_demos)
            hist_pts = _positions(hist_demos)

            if not recent_pts or not hist_pts:
                return 0.0

            # 3. Compare Distributions (Simplified Centroid Drift)
            # Guard: filter incomplete/None tuples and ensure uniform shape (F2-44)
            recent_clean = [
                p
                for p in recent_pts
                if p is not None and len(p) == 2 and all(v is not None for v in p)
            ]
            hist_clean = [
                p
                for p in hist_pts
                if p is not None and len(p) == 2 and all(v is not None for v in p)
            ]
            if not recent_clean or not hist_clean:
                return 0.0

            r_centroid = np.mean(recent_clean, axis=0)
            h_centroid = np.mean(hist_clean, axis=0)

            dist = float(np.linalg.norm(r_centroid - h_centroid))

            # P-MD-01: Use actual map dimensions from spatial_data when available.
            # Falls back to observed data spread only if map metadata is missing.
            from Programma_CS2_RENAN.core.spatial_data import get_map_metadata

            meta = get_map_metadata(map_name)
            if meta:
                # Map extent = scale * radar_resolution (1024 pixels)
                map_extent = meta.scale * 1024.0
            else:
                all_pts = np.array(recent_clean + hist_clean)
                map_extent = max(float(np.ptp(all_pts[:, 0])), float(np.ptp(all_pts[:, 1])), 1.0)
            # Normalize: 10% of map extent drift = 1.0 coefficient
            drift_threshold = max(map_extent * 0.10, 500.0)
            return min(dist / drift_threshold, 1.0)

    @staticmethod
    def calculate_drift_coefficient(map_name: str = None) -> float:
        """
        Returns a value between 0.0 (Stable) and 1.0 (Meta Chaos).
        Combines Statistical Drift (Rating) and Spatial Drift (Positioning).
        """
        stat_drift = 0.0

        # ProPlayerStatCard lives in hltv_metadata.db
        hltv_db = get_hltv_db_manager()
        with hltv_db.get_session() as s:
            # 1. Statistical Drift
            hist_avg = s.exec(select(func.avg(ProPlayerStatCard.rating_2_0))).one() or 0.0
            # P-MD-02: If historical avg is near-zero, data is degenerate — no drift to measure.
            if abs(hist_avg) < 0.1:
                stat_drift = 0.0
            else:
                limit_date = datetime.now(timezone.utc) - timedelta(days=30)
                recent_avg_raw = s.exec(
                    select(func.avg(ProPlayerStatCard.rating_2_0)).where(
                        ProPlayerStatCard.last_updated >= limit_date
                    )
                ).one()
                recent_avg = recent_avg_raw if recent_avg_raw is not None else hist_avg
                stat_drift = min((abs(recent_avg - hist_avg) / hist_avg) / 0.20, 1.0)

        # 2. Spatial Drift (if map provided)
        spatial_drift = 0.0
        if map_name:
            spatial_drift = MetaDriftEngine.calculate_spatial_drift(map_name)

        # P-MD-03: Named weights for drift combination.
        # Spatial drift weighted higher because positioning changes reflect
        # meta shifts faster than rating averages.
        _WEIGHT_STAT_DRIFT = 0.4
        _WEIGHT_SPATIAL_DRIFT = 0.6
        if map_name:
            return (stat_drift * _WEIGHT_STAT_DRIFT) + (spatial_drift * _WEIGHT_SPATIAL_DRIFT)
        return stat_drift

    @staticmethod
    def get_meta_confidence_adjustment(map_name: str = None) -> float:
        """
        Returns a multiplier for Coach Confidence.
        """
        drift = MetaDriftEngine.calculate_drift_coefficient(map_name)
        return 1.0 - (drift * 0.5)
