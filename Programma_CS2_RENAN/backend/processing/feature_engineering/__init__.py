"""Feature Engineering Module."""

from Programma_CS2_RENAN.backend.processing.feature_engineering.kast import (
    calculate_kast_for_round,
    calculate_kast_percentage,
    estimate_kast_from_stats,
)
from Programma_CS2_RENAN.backend.processing.feature_engineering.role_features import (
    PlayerRole,
    classify_role,
    extract_role_features,
    get_role_coaching_focus,
)
from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
    METADATA_DIM,
    FeatureExtractor,
)

__all__ = [
    "FeatureExtractor",
    "METADATA_DIM",
    "calculate_kast_for_round",
    "calculate_kast_percentage",
    "estimate_kast_from_stats",
    "PlayerRole",
    "classify_role",
    "extract_role_features",
    "get_role_coaching_focus",
]
