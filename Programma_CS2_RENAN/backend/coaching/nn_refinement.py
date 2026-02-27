def apply_nn_refinement(corrections, nn_adjustments):
    refined = []

    for c in corrections:
        feature = c["feature"]

        adjustment = nn_adjustments.get(f"{feature}_weight", 0.0)
        refined_z = c["weighted_z"] * (1 + adjustment)

        refined.append({**c, "weighted_z": refined_z})

    return refined
