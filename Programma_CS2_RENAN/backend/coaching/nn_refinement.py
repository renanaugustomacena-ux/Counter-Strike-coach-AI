"""
Correction Weight Scaling (DA-03: renamed from "NN Refinement")

Scales pre-computed coaching correction Z-scores by feature-specific weight
adjustments. Despite the historical module name, this function performs simple
scalar multiplication — it does NOT invoke any neural network, load any model,
or perform inference. The nn_adjustments dict is expected to contain float
weights keyed by "{feature}_weight"; these may originate from an NN model's
output, but this module itself is a pure arithmetic scaling step.
"""

from typing import Any, Dict, List

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.coaching.nn_refinement")


def apply_nn_refinement(
    corrections: List[Dict[str, Any]],
    nn_adjustments: Dict[str, float],
) -> List[Dict[str, Any]]:
    refined: List[Dict[str, Any]] = []

    for c in corrections:
        feature = c["feature"]

        adjustment = nn_adjustments.get(f"{feature}_weight", 0.0)
        refined_z = c["weighted_z"] * (1 + adjustment)

        refined.append({**c, "weighted_z": refined_z})

    logger.debug("NN refinement applied to %d corrections", len(refined))
    return refined
