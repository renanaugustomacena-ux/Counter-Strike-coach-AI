from typing import Any, Dict

import pandas as pd

from Programma_CS2_RENAN.backend.processing.external_analytics import EliteAnalytics
from Programma_CS2_RENAN.backend.processing.validation.drift import detect_feature_drift
from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats


class AnalysisService:
    def __init__(self):
        self.elite_analytics = EliteAnalytics()
        self.db_manager = get_db_manager()

    def analyze_latest_performance(self, player_name: str) -> Dict[str, Any]:
        """
        Retrieves latest match stats from DB and runs comparative analytics.
        """
        from sqlmodel import select

        with self.db_manager.get_session() as session:
            stmt = (
                select(PlayerMatchStats)
                .where(PlayerMatchStats.player_name == player_name)
                .order_by(PlayerMatchStats.processed_at.desc())
            )
            latest = session.exec(stmt).first()
        return self._prepare_latest_response(player_name, latest)

    def _prepare_latest_response(self, player_name, latest):
        if not latest:
            return {"status": "error", "message": f"No data found for {player_name}"}
        return {
            "status": "success",
            "player": player_name,
            "stats": latest.model_dump(),
            "message": "Latest performance retrieved.",
        }

    def get_pro_comparison(self, player_name: str, pro_name: str) -> Dict[str, Any]:
        """
        Fetches stats for a user and a pro, and prepares comparison data.
        """
        from sqlmodel import select

        with self.db_manager.get_session() as session:
            user_stats = session.exec(
                select(PlayerMatchStats).where(PlayerMatchStats.player_name == player_name)
            ).first()
            pro_stats = session.exec(
                select(PlayerMatchStats).where(PlayerMatchStats.player_name == pro_name)
            ).first()
        return self._prepare_comparison_response(player_name, pro_name, user_stats, pro_stats)

    def _prepare_comparison_response(self, player_name, pro_name, user_stats, pro_stats):
        if not user_stats or not pro_stats:
            return {"status": "error", "message": "Player or Pro not found"}
        return {
            "status": "success",
            "user_name": player_name,
            "pro_name": pro_name,
            "user_data": user_stats.model_dump(),
            "pro_data": pro_stats.model_dump(),
        }

    def check_for_drift(self, player_name: str) -> Dict[str, float]:
        """
        Checks for performance drift in the player's history.
        Returns dict of feature drift scores, or empty dict if insufficient data.
        """
        from sqlmodel import select

        with self.db_manager.get_session() as session:
            history = session.exec(
                select(PlayerMatchStats)
                .where(PlayerMatchStats.player_name == player_name)
                .order_by(PlayerMatchStats.processed_at.desc())
                .limit(100)
            ).all()

        if len(history) < 2:
            return {}

        history_dicts = [h.model_dump() for h in history]
        df = pd.DataFrame(history_dicts)
        return detect_feature_drift(df)


def get_analysis_service() -> AnalysisService:
    return AnalysisService()
