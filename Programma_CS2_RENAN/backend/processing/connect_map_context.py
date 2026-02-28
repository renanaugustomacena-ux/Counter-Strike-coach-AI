from typing import List, Tuple, Union

import numpy as np

# Multi-level map configuration (Task 2.17.1: Verticality Awareness)
# Maps with significant Z-axis gameplay (Nuke, Vertigo)
Z_LEVEL_THRESHOLD = 200  # Units separating level floors
Z_PENALTY_FACTOR = 2.0  # Multiplier for cross-level distance
# NOTE (F2-46): Distance normalisation constants below are fixed per-map values.
# If spatial_data.py is updated with new map scales/bounds, these constants must
# be updated manually — there is no automatic synchronisation.


def distance_with_z_penalty(
    player_pos: Union[Tuple, List, np.ndarray],
    target_pos: Union[Tuple, List, np.ndarray],
    z_penalty_factor: float = Z_PENALTY_FACTOR,
    z_threshold: float = Z_LEVEL_THRESHOLD,
) -> float:
    """
    Calculate distance with Z-axis penalty for multi-level maps.

    On single-level maps, behaves like standard Euclidean distance.
    On multi-level maps (Nuke, Vertigo), applies penalty when player
    and target are on different floors to prevent false proximity readings.

    Args:
        player_pos: Player position (x, y) or (x, y, z)
        target_pos: Target position (x, y) or (x, y, z)
        z_penalty_factor: Multiplier for Z-difference when on different levels
        z_threshold: Minimum Z-difference to consider as different levels

    Returns:
        float: Distance with Z-penalty applied
    """
    player = np.array(player_pos)
    target = np.array(target_pos)

    # Handle 2D vs 3D coordinates
    if len(player) < 3 or len(target) < 3:
        # 2D fallback - standard Euclidean
        return float(np.linalg.norm(player[:2] - target[:2]))

    # Calculate XY (horizontal) distance
    xy_dist = np.linalg.norm(player[:2] - target[:2])

    # Calculate Z (vertical) difference
    z_diff = abs(player[2] - target[2])

    # Apply penalty only if Z-difference indicates different levels
    if z_diff > z_threshold:
        # Player and target are on different floors
        # Penalize the Z-difference to indicate tactical separation
        return float(xy_dist + (z_diff * z_penalty_factor))

    # Same level - use standard 3D Euclidean distance
    return float(np.linalg.norm(player - target))


def calculate_map_context_features(player_pos, map_tensors, feature_dim=6):
    """
    Calculates spatial features relative to map objectives.

    Now includes Z-axis awareness for multi-level maps (Nuke, Vertigo).
    When player and objective are on different floors, distance is penalized
    to prevent false "close to site" readings.

    Args:
        player_pos (tuple): (x, y, z) of the player.
        map_tensors (dict): Dictionary containing map objectives (bombsites, spawns, etc.).
        feature_dim (int): Number of features to generate.

    Returns:
        np.array: Normalized feature vector of size feature_dim.
    """
    if not map_tensors:
        return np.zeros(feature_dim)

    features = []

    # 1. Distance to Bombsites (with Z-penalty for multi-level maps)
    bombsites = map_tensors.get("bombsites", {})
    for site in ["A", "B"]:
        if site in bombsites:
            target = bombsites[site]
            # Use Z-aware distance calculation
            dist = distance_with_z_penalty(player_pos, target)
            # Normalize: assume max map distance approx 4000 units
            features.append(np.clip(dist / 4000.0, 0, 1))
        else:
            features.append(1.0)  # Far away if unknown

    # 2. Distance to Spawns (Control Zones)
    spawns = map_tensors.get("spawns", {})
    for side in ["T", "CT"]:
        if side in spawns:
            target = spawns[side]
            dist = distance_with_z_penalty(player_pos, target)
            features.append(np.clip(dist / 4000.0, 0, 1))
        else:
            features.append(1.0)

    # 3. Distance to Mid Control (if defined)
    mid = map_tensors.get("mid_control")
    if mid:
        dist = distance_with_z_penalty(player_pos, mid)
        features.append(np.clip(dist / 4000.0, 0, 1))
    else:
        features.append(1.0)

    # Pad or truncate to ensure fixed dimension
    if len(features) < feature_dim:
        features.extend([0.0] * (feature_dim - len(features)))

    return np.array(features[:feature_dim])
