from Programma_CS2_RENAN.core.config import get_setting

# Default feature importance weights for coaching prioritisation
DEFAULT_IMPORTANCE = {
    "avg_kast": 1.5,
    "avg_adr": 1.5,
    "avg_hs": 1.2,
    "impact_rounds": 1.3,
    "positional_aggression_score": 1.0,
    "accuracy": 1.4,
    "econ_rating": 1.1,
}


def get_feature_importance(feature):
    """Retrieves weight with user-setting override support."""
    overrides = get_setting("COACH_WEIGHT_OVERRIDES", {})
    return overrides.get(feature, DEFAULT_IMPORTANCE.get(feature, 1.0))


CONFIDENCE_ROUNDS_CEILING = 300


def generate_corrections(deviations, rounds_played, nn_adjustments=None):
    confidence = min(1.0, rounds_played / CONFIDENCE_ROUNDS_CEILING)
    corrections = []

    for feature, val in deviations.items():
        # Handle both float (legacy) and tuple (new standard) inputs
        z = val[0] if isinstance(val, tuple) else val

        weighted = z * confidence
        corrections.append(
            {
                "feature": feature,
                "weighted_z": weighted,
                "importance": get_feature_importance(feature),
            }
        )

    if nn_adjustments:
        from Programma_CS2_RENAN.backend.coaching.nn_refinement import apply_nn_refinement

        corrections = apply_nn_refinement(corrections, nn_adjustments)

    return sorted(corrections, key=lambda x: abs(x["weighted_z"]) * x["importance"], reverse=True)[
        :3
    ]
