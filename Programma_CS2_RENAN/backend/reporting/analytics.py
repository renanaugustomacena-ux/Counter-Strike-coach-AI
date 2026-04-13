import re

import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlmodel import select

from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import CoachState, PlayerMatchStats
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.analytics")


class AnalyticsEngine:
    """
    Centralized math engine for Dashboard Analytics.
    Decouples data aggregation from UI rendering.

    When the user has no personal matches (is_pro=False), queries fall back
    to ALL matches (including pro) so the Performance screen shows data
    rather than an empty state.
    """

    def __init__(self):
        self.db = get_db_manager()

    def _player_filter(self, player_name: str):
        """Build WHERE clause: user matches first, fallback to all matches."""
        from sqlmodel import select as _sel

        with self.db.get_session() as session:
            user_count = session.exec(
                _sel(func.count(PlayerMatchStats.id)).where(
                    PlayerMatchStats.player_name == player_name,
                    PlayerMatchStats.is_pro == False,  # noqa: E712
                )
            ).one()

        if user_count and user_count > 0:
            # User has personal matches — filter to those
            return (
                PlayerMatchStats.player_name == player_name,
                PlayerMatchStats.is_pro == False,  # noqa: E712
            )
        else:
            # No personal matches — show all data (pro overview mode)
            return (True,)  # No filter — all rows

    def get_player_trends(self, player_name: str, limit: int = 20) -> pd.DataFrame:
        """
        Fetches historical performance metrics for the trend graph.
        """
        filters = self._player_filter(player_name)
        with self.db.get_session() as session:
            stmt = (
                select(PlayerMatchStats)
                .where(*filters)
                .order_by(PlayerMatchStats.processed_at.desc())
                .limit(limit)
            )

            results = session.exec(stmt).all()
            if not results:
                return pd.DataFrame()

            # Convert to DataFrame and reverse to chronological order
            data = [r.model_dump() for r in results]
            df = pd.DataFrame(data).iloc[::-1]
            return df

    def get_skill_radar(self, player_name: str) -> dict:
        """
        Computes normalized skill attributes (0-100) compared to Pro Baseline.
        """
        # 1. Fetch User Averages
        with self.db.get_session() as session:
            stmt = select(
                func.avg(PlayerMatchStats.accuracy).label("avg_acc"),
                func.avg(PlayerMatchStats.avg_hs).label("avg_hs"),
                func.avg(PlayerMatchStats.avg_kast).label("avg_kast"),
                func.avg(PlayerMatchStats.utility_enemies_blinded).label("avg_util_blind"),
                func.avg(PlayerMatchStats.utility_blind_time).label("avg_util_time"),
                func.avg(PlayerMatchStats.flash_assists).label("avg_flash"),
                func.avg(PlayerMatchStats.avg_adr).label("avg_adr"),
                func.avg(PlayerMatchStats.clutch_win_pct).label("avg_clutch"),
            ).where(PlayerMatchStats.player_name == player_name)

            user_stats = session.exec(stmt).first()
            if not user_stats or user_stats[0] is None:
                return {}  # Not enough data

        # 2. Heuristic Mapping (Simplified for V1)
        # SA-03: aggregate select() returns Row objects — use integer indexing,
        # not attribute access (Row doesn't support .avg_acc etc.)
        avg_acc = float(user_stats[0] or 0)
        avg_hs = float(user_stats[1] or 0)
        avg_kast = float(user_stats[2] or 0)
        avg_util_blind = float(user_stats[3] or 0)
        avg_util_time = float(user_stats[4] or 0)
        avg_flash = float(user_stats[5] or 0)
        avg_adr = float(user_stats[6] or 0)
        avg_clutch = float(user_stats[7] or 0)

        # Aim: Accuracy & HS%
        aim = (avg_acc * 100 * 0.5) + (avg_hs * 100 * 0.5)

        # Utility: Blinded Enemies & Blind Time
        # Heuristic: 2.0 enemies/round = 100pts
        util_score = min(100, (avg_util_blind / 2.0) * 100)
        flash_score = min(100, (avg_flash / 1.0) * 100)
        utility = (util_score * 0.6) + (flash_score * 0.4)

        # Positioning: KAST & Survival
        # KAST > 75% = 100pts
        positioning = min(100, (avg_kast / 0.75) * 100)

        # Sense: ADR & EF
        # ADR > 100 = 100pts
        sense = min(100, (avg_adr / 100.0) * 100)

        # Clutch: Win Pct
        clutch = min(100, avg_clutch * 100)

        return {
            "Aim": int(aim),
            "Utility": int(utility),
            "Positioning": int(positioning),
            "Map Sense": int(sense),
            "Clutch": int(clutch),
        }

    def get_training_metrics(self) -> dict:
        """Fetches latest training telemetry."""
        with self.db.get_session("knowledge") as session:
            state = session.exec(select(CoachState)).first()
            if not state:
                return {}
            return {
                "epoch": state.current_epoch,
                "total_epochs": state.total_epochs,
                "loss": state.train_loss,
                "val_loss": state.val_loss,
                "confidence": state.belief_confidence,
            }

    def get_rating_history(self, player_name: str, limit: int = 50) -> list:
        """Returns list of {rating, match_date, demo_name} ordered chronologically."""
        try:
            filters = self._player_filter(player_name)
            with self.db.get_session() as session:
                stmt = (
                    select(
                        PlayerMatchStats.rating,
                        PlayerMatchStats.match_date,
                        PlayerMatchStats.demo_name,
                    )
                    .where(*filters)
                    .order_by(PlayerMatchStats.match_date.desc())
                    .limit(limit)
                )
                results = session.exec(stmt).all()
                if not results:
                    return []
                return [
                    {"rating": r[0], "match_date": r[1], "demo_name": r[2]}
                    for r in reversed(results)
                ]
        except Exception as e:
            logger.error("analytics.get_rating_history failed: %s", e)
            return []

    def get_per_map_stats(self, player_name: str) -> dict:
        """Aggregates per-map performance: {map_name: {rating, adr, kd, matches}}."""
        # Match standard CS2 map names (de_mirage, cs_office) and also
        # map names embedded in demo filenames like "furia-vs-navi-m1-mirage.dem"
        _KNOWN_MAPS = {
            "mirage",
            "inferno",
            "dust2",
            "overpass",
            "ancient",
            "anubis",
            "nuke",
            "vertigo",
            "train",
            "cache",
            "office",
        }
        _MAP_PATTERN = re.compile(r"(de_\w+|cs_\w+|ar_\w+)")
        try:
            filters = self._player_filter(player_name)
            with self.db.get_session() as session:
                stmt = select(PlayerMatchStats).where(*filters)
                results = session.exec(stmt).all()
                if not results:
                    return {}

                map_groups: dict[str, list] = {}
                for m in results:
                    demo = (m.demo_name or "").lower()
                    match = _MAP_PATTERN.search(demo)
                    if match:
                        map_name = match.group(1)
                    else:
                        # Try known map names in the demo filename (e.g., "m1-mirage.dem")
                        map_name = "unknown"
                        for known in _KNOWN_MAPS:
                            if known in demo:
                                map_name = f"de_{known}"
                                break
                    map_groups.setdefault(map_name, []).append(m)

                per_map = {}
                for map_name, matches in map_groups.items():
                    ratings = [m.rating for m in matches if m.rating]
                    adrs = [m.avg_adr for m in matches if m.avg_adr]
                    kds = [m.kd_ratio for m in matches if m.kd_ratio]
                    per_map[map_name] = {
                        "rating": float(np.mean(ratings)) if ratings else 1.0,
                        "adr": float(np.mean(adrs)) if adrs else 0.0,
                        "kd": float(np.mean(kds)) if kds else 1.0,
                        "matches": len(matches),
                    }
                return per_map
        except Exception as e:
            logger.error("analytics.get_per_map_stats failed: %s", e)
            return {}

    def get_strength_weakness(self, player_name: str) -> dict:
        """Computes Z-score deviations vs pro baseline for key metrics."""
        from Programma_CS2_RENAN.backend.processing.baselines.pro_baseline import (
            calculate_deviations,
            get_pro_baseline,
        )

        try:
            filters = self._player_filter(player_name)
            with self.db.get_session() as session:
                stmt = select(
                    func.avg(PlayerMatchStats.rating).label("rating"),
                    func.avg(PlayerMatchStats.kd_ratio).label("kd_ratio"),
                    func.avg(PlayerMatchStats.avg_adr).label("avg_adr"),
                    func.avg(PlayerMatchStats.avg_kast).label("avg_kast"),
                    func.avg(PlayerMatchStats.avg_hs).label("avg_hs"),
                    func.avg(PlayerMatchStats.accuracy).label("accuracy"),
                    func.avg(PlayerMatchStats.clutch_win_pct).label("clutch_win_pct"),
                    func.avg(PlayerMatchStats.opening_duel_win_pct).label("opening_duel_win_pct"),
                ).where(*filters)
                row = session.exec(stmt).first()
                if not row or row[0] is None:
                    return {"strengths": [], "weaknesses": []}

            player_stats = {
                "rating": row[0] or 0,
                "kd_ratio": row[1] or 0,
                "avg_adr": row[2] or 0,
                "avg_kast": row[3] or 0,
                "avg_hs": row[4] or 0,
                "accuracy": row[5] or 0,
                "clutch_win_pct": row[6] or 0,
                "opening_duel_win_pct": row[7] or 0,
            }

            baseline = get_pro_baseline()
            deviations = calculate_deviations(player_stats, baseline)

            display_names = {
                "rating": "Rating",
                "kd_ratio": "K/D Ratio",
                "avg_adr": "ADR",
                "avg_kast": "KAST",
                "avg_hs": "Headshot %",
                "accuracy": "Accuracy",
                "clutch_win_pct": "Clutch Win %",
                "opening_duel_win_pct": "Opening Duel %",
            }

            strengths, weaknesses = [], []
            for metric, (z_score, _raw) in deviations.items():
                name = display_names.get(metric, metric)
                if z_score > 0.5:
                    strengths.append((name, round(z_score, 2)))
                elif z_score < -0.5:
                    weaknesses.append((name, round(z_score, 2)))

            strengths.sort(key=lambda x: x[1], reverse=True)
            weaknesses.sort(key=lambda x: x[1])
            return {"strengths": strengths[:5], "weaknesses": weaknesses[:5]}
        except Exception as e:
            logger.error("analytics.get_strength_weakness failed: %s", e)
            return {"strengths": [], "weaknesses": []}

    def get_utility_breakdown(self, player_name: str) -> dict:
        """Per-utility comparison: user vs pro baseline for 6 utility metrics."""
        try:
            filters = self._player_filter(player_name)
            with self.db.get_session() as session:
                stmt = select(
                    func.avg(PlayerMatchStats.he_damage_per_round).label("he_dmg"),
                    func.avg(PlayerMatchStats.molotov_damage_per_round).label("molotov_dmg"),
                    func.avg(PlayerMatchStats.smokes_per_round).label("smokes"),
                    func.avg(PlayerMatchStats.utility_blind_time).label("flash_blind"),
                    func.avg(PlayerMatchStats.flash_assists).label("flash_assists"),
                    func.avg(PlayerMatchStats.unused_utility_per_round).label("unused_util"),
                ).where(*filters)
                row = session.exec(stmt).first()
                if not row or row[0] is None:
                    return {}

            user = {
                "he_damage": float(row[0] or 0),
                "molotov_damage": float(row[1] or 0),
                "smokes_per_round": float(row[2] or 0),
                "flash_blind_time": float(row[3] or 0),
                "flash_assists": float(row[4] or 0),
                "unused_utility": float(row[5] or 0),
            }

            # Query real pro utility averages from DB
            pro_stmt = select(
                func.avg(PlayerMatchStats.he_damage_per_round),
                func.avg(PlayerMatchStats.molotov_damage_per_round),
                func.avg(PlayerMatchStats.smokes_per_round),
                func.avg(PlayerMatchStats.utility_blind_time),
                func.avg(PlayerMatchStats.flash_assists),
                func.avg(PlayerMatchStats.unused_utility_per_round),
            ).where(
                PlayerMatchStats.is_pro == True
            )  # noqa: E712
            with self.db.get_session() as session:
                pro_row = session.exec(pro_stmt).first()

            if pro_row and pro_row[0] is not None:
                pro = {
                    "he_damage": float(pro_row[0] or 0),
                    "molotov_damage": float(pro_row[1] or 0),
                    "smokes_per_round": float(pro_row[2] or 0),
                    "flash_blind_time": float(pro_row[3] or 0),
                    "flash_assists": float(pro_row[4] or 0),
                    "unused_utility": float(pro_row[5] or 0),
                    "_provenance": "db",
                }
            else:
                # No pro data in DB — return empty rather than fabricate values (Anti-Fabrication Rule).
                logger.info("No pro utility data in DB; returning empty pro baseline")
                pro = {}
            return {"user": user, "pro": pro}
        except Exception as e:
            logger.error("analytics.get_utility_breakdown failed: %s", e)
            return {}

    def get_hltv2_breakdown(self, player_name: str) -> dict:
        """Returns the 5 HLTV 2.0 rating components for the player's average stats."""
        from Programma_CS2_RENAN.backend.processing.feature_engineering.rating import (
            BASELINE_ADR,
            BASELINE_DPR_COMPLEMENT,
            BASELINE_IMPACT,
            BASELINE_KAST,
            BASELINE_KPR,
            compute_impact_rating,
            compute_survival_rating,
        )

        try:
            filters = self._player_filter(player_name)
            with self.db.get_session() as session:
                stmt = select(
                    func.avg(PlayerMatchStats.kpr).label("kpr"),
                    func.avg(PlayerMatchStats.dpr).label("dpr"),
                    func.avg(PlayerMatchStats.avg_kast).label("kast"),
                    func.avg(PlayerMatchStats.avg_adr).label("adr"),
                ).where(*filters)
                row = session.exec(stmt).first()
                if not row or row[0] is None:
                    return {}

            kpr = float(row[0] or 0)
            dpr = float(row[1] or 0)
            kast = float(row[2] or 0)
            adr = float(row[3] or 0)

            impact = compute_impact_rating(kpr, adr)
            survival = compute_survival_rating(dpr)

            return {
                "Kill": round(kpr / BASELINE_KPR, 3) if BASELINE_KPR else 0,
                "Survival": (
                    round(survival / BASELINE_DPR_COMPLEMENT, 3) if BASELINE_DPR_COMPLEMENT else 0
                ),
                "KAST": round(kast / BASELINE_KAST, 3) if BASELINE_KAST else 0,
                "Impact": round(impact / BASELINE_IMPACT, 3) if BASELINE_IMPACT else 0,
                "Damage": round(adr / BASELINE_ADR, 3) if BASELINE_ADR else 0,
            }
        except Exception as e:
            logger.error("analytics.get_hltv2_breakdown failed: %s", e)
            return {}


# Global Instance
analytics = AnalyticsEngine()
