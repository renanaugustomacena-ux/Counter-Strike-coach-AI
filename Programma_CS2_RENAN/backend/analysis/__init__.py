"""
Analysis Engines Package

Provides advanced analysis tools for CS2 coaching:
- Win Probability Predictor
- Role Classifier
- Utility Analyzer
- Economy Optimizer
"""

from Programma_CS2_RENAN.backend.analysis.belief_model import (
    DeathProbabilityEstimator,
    get_death_estimator,
)
from Programma_CS2_RENAN.backend.analysis.blind_spots import (
    BlindSpotDetector,
    get_blind_spot_detector,
)
from Programma_CS2_RENAN.backend.analysis.deception_index import (
    DeceptionAnalyzer,
    get_deception_analyzer,
)
from Programma_CS2_RENAN.backend.analysis.engagement_range import (
    EngagementRangeAnalyzer,
    get_engagement_range_analyzer,
)
from Programma_CS2_RENAN.backend.analysis.entropy_analysis import (
    EntropyAnalyzer,
    get_entropy_analyzer,
)
from Programma_CS2_RENAN.backend.analysis.game_tree import (
    ExpectiminimaxSearch,
    get_game_tree_search,
)
from Programma_CS2_RENAN.backend.analysis.momentum import MomentumTracker, get_momentum_tracker
from Programma_CS2_RENAN.backend.analysis.role_classifier import (
    ROLE_PROFILES,
    PlayerRole,
    RoleClassifier,
    RoleProfile,
    get_role_classifier,
)
from Programma_CS2_RENAN.backend.analysis.utility_economy import (
    EconomyDecision,
    EconomyOptimizer,
    UtilityAnalyzer,
    UtilityReport,
    UtilityType,
    get_economy_optimizer,
    get_utility_analyzer,
)
from Programma_CS2_RENAN.backend.analysis.win_probability import (
    GameState,
    WinProbabilityNN,
    WinProbabilityPredictor,
    get_win_predictor,
)

__all__ = [
    # Win Probability
    "WinProbabilityPredictor",
    "WinProbabilityNN",
    "GameState",
    "get_win_predictor",
    # Role Classifier
    "RoleClassifier",
    "PlayerRole",
    "RoleProfile",
    "ROLE_PROFILES",
    "get_role_classifier",
    # Utility & Economy
    "UtilityAnalyzer",
    "EconomyOptimizer",
    "UtilityType",
    "UtilityReport",
    "EconomyDecision",
    "get_utility_analyzer",
    "get_economy_optimizer",
    # Phase 6 Analysis Engines — classes
    "DeathProbabilityEstimator",
    "DeceptionAnalyzer",
    "MomentumTracker",
    "EntropyAnalyzer",
    "ExpectiminimaxSearch",
    "BlindSpotDetector",
    "EngagementRangeAnalyzer",
    # Phase 6 Analysis Engines — factory functions
    "get_death_estimator",
    "get_deception_analyzer",
    "get_momentum_tracker",
    "get_entropy_analyzer",
    "get_game_tree_search",
    "get_blind_spot_detector",
    "get_engagement_range_analyzer",
]
