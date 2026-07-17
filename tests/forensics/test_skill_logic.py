"""
FORENSIC TEST SUITE - SKILL MODEL VALIDATION
Implementation of Step 11 [TESTABILITY]: Unit Test Harness for SkillModel.
"""

import pytest
import torch

from Programma_CS2_RENAN.backend.nn.rap_coach.skill_model import SkillAxes, SkillLatentModel
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats


def test_beginner_skill_levels():
    """Verify that a beginner-style stat card results in low levels.

    The card is COMPLETE, as production writers emit it (demo_parser /
    aggregate_match_stats_sql): the rating_* components are raw-scale
    (rating_survival = 1 - dpr, rating_kast = kast, rating_impact = HLTV
    impact). Since the 0.0-is-real fix (R4), absent components would count
    as genuine zeros — a realistic row always carries them.
    """
    stats = PlayerMatchStats(
        player_name="Noob",
        demo_name="test_1",
        accuracy=0.05,
        avg_hs=0.10,
        avg_deaths=1.5,
        avg_kast=0.40,
        opening_duel_win_pct=0.20,
        clutch_win_pct=0.05,
        utility_blind_time=1.0,
        utility_enemies_blinded=0.1,
        positional_aggression_score=0.1,
        rating_survival=-0.5,  # 1 - dpr with dpr=1.5, as demo_parser writes it
        rating_kast=0.40,  # mirrors avg_kast (raw scale)
        rating_impact=0.45,  # low HLTV impact, raw scale
    )

    vec = SkillLatentModel.calculate_skill_vector(stats)
    level = SkillLatentModel.get_curriculum_level(vec)

    print(f"Beginner Level: {level}/10 (Axes: {vec})")
    assert level <= 3, f"Beginner should be level 1-3, got {level}"


def test_pro_skill_levels():
    """Verify that a professional-style stat card results in high levels.

    Complete card in the raw component scale production writers emit —
    see test_beginner_skill_levels docstring.
    """
    stats = PlayerMatchStats(
        player_name="Pro",
        demo_name="test_2",
        accuracy=0.35,
        avg_hs=0.65,
        avg_deaths=0.5,
        avg_kast=0.85,
        opening_duel_win_pct=0.75,
        clutch_win_pct=0.55,
        utility_blind_time=25.0,
        utility_enemies_blinded=4.5,
        positional_aggression_score=0.8,
        rating_survival=0.5,  # 1 - dpr with dpr=0.5 (raw scale)
        rating_kast=0.85,  # mirrors avg_kast (raw scale)
        rating_impact=1.40,  # strong-pro HLTV impact, raw scale
    )

    vec = SkillLatentModel.calculate_skill_vector(stats)
    level = SkillLatentModel.get_curriculum_level(vec)

    print(f"Pro Level: {level}/10 (Axes: {vec})")
    assert level >= 8, f"Pro should be level 8-10, got {level}"


def test_skill_tensor_onehot():
    """Ensure the skill tensor is a valid one-hot 10-dim vector."""
    vec = {
        ax: 0.5
        for ax in [
            SkillAxes.MECHANICS,
            SkillAxes.POSITIONING,
            SkillAxes.UTILITY,
            SkillAxes.TIMING,
            SkillAxes.DECISION,
        ]
    }
    tensor = SkillLatentModel.get_skill_tensor(vec)

    assert tensor.shape == (1, 10)
    assert torch.sum(tensor) == 1.0
    assert tensor[0, 4] == 1.0  # Level 5 should be index 4
