from typing import Dict, List

import numpy as np
import torch

from Programma_CS2_RENAN.backend.processing.baselines.pro_baseline import get_pro_baseline
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats


class SkillAxes:
    MECHANICS = "mechanics"  # Aim, HS%, Movement
    POSITIONING = "positioning"  # Aggression, Exposure, Map Control
    UTILITY = "utility"  # Blind time, Enemies blinded
    TIMING = "timing"  # Opening duels, Rotation speed
    DECISION = "decision"  # Clutch wins, ADR efficiency

    @classmethod
    def all(cls):
        return [cls.MECHANICS, cls.POSITIONING, cls.UTILITY, cls.TIMING, cls.DECISION]


class SkillLatentModel:
    """
    Implementation of Phase 5: Skill & Curriculum Layer.
    Decomposes aggregate stats into 5 axes and projects onto 1-10 scale.
    """

    @staticmethod
    def calculate_skill_vector(stats: PlayerMatchStats) -> Dict[str, float]:
        """
        Calculates normalized skill scores (0.0 to 1.0) for each axis.
        Using a more sensitive Gaussian normalization (Z-score to Percentile).
        """
        baseline = get_pro_baseline()

        def get_z(feat, val):
            # Check for missing/zero data
            if not val or feat not in baseline:
                return None  # Mark as unavailable

            b = baseline[feat]
            z = (val - b["mean"]) / max(1e-6, b["std"])
            percentile = 1.0 / (1.0 + np.exp(-1.702 * z))
            return np.clip(percentile, 0, 1)

        # Calculate all axes
        results = {}

        # 1. Mechanics (Pure Aim & Tech)
        m_vals = [get_z("accuracy", stats.accuracy), get_z("avg_hs", stats.avg_hs)]
        m_vals = [v for v in m_vals if v is not None]
        if m_vals:
            results[SkillAxes.MECHANICS] = np.mean(m_vals)

        # 2. Positioning (Smart Positioning: Survival & Participation)
        # Decoupled from Aggression/Deaths. High survival = Good Positioning.
        p_vals = [
            get_z("rating_survival", stats.rating_survival),
            get_z(
                "rating_kast", stats.rating_kast
            ),  # KAST implies being in position to trade/survive
        ]
        p_vals = [v for v in p_vals if v is not None]
        if p_vals:
            results[SkillAxes.POSITIONING] = np.mean(p_vals)

        # 3. Utility
        u_vals = [
            get_z("utility_blind_time", stats.utility_blind_time),
            get_z("utility_enemies_blinded", stats.utility_enemies_blinded),
        ]
        u_vals = [v for v in u_vals if v is not None]
        if u_vals:
            results[SkillAxes.UTILITY] = np.mean(u_vals)

        # 4. Timing (Space Taking & Aggression)
        # Aggression is a Timing skill (knowing WHEN to push).
        t_vals = [
            get_z("opening_duel_win_pct", stats.opening_duel_win_pct),
            get_z("positional_aggression_score", stats.positional_aggression_score),
        ]
        t_vals = [v for v in t_vals if v is not None]
        if t_vals:
            results[SkillAxes.TIMING] = np.mean(t_vals)

        # 5. Decision (Impact & Clutch)
        # Impact correlates with making the RIGHT play.
        d_vals = [
            get_z("clutch_win_pct", stats.clutch_win_pct),
            get_z("rating_impact", stats.rating_impact),
        ]
        d_vals = [v for v in d_vals if v is not None]
        if d_vals:
            results[SkillAxes.DECISION] = np.mean(d_vals)

        # Fallback if everything is empty
        if not results:
            return {
                ax: 0.5
                for ax in [
                    SkillAxes.MECHANICS,
                    SkillAxes.POSITIONING,
                    SkillAxes.UTILITY,
                    SkillAxes.TIMING,
                    SkillAxes.DECISION,
                ]
            }

        return results

    @staticmethod
    def get_curriculum_level(skill_vec: Dict[str, float]) -> int:
        """
        Maps the average skill score to a 1-10 index.
        """
        if not skill_vec:
            return 1
        avg_skill = sum(skill_vec.values()) / len(skill_vec)
        # Scale 0..1 to 1..10
        level = int(avg_skill * 9) + 1
        return max(1, min(10, level))

    @staticmethod
    def get_skill_tensor(skill_vec: Dict[str, float]) -> torch.Tensor:
        """
        Converts the 5-axis vector into a 10-dim one-hot level tensor for RAPPedagogy.
        """
        level = SkillLatentModel.get_curriculum_level(skill_vec)
        tensor = torch.zeros(1, 10)
        tensor[0, level - 1] = 1.0
        return tensor
