"""
Bombsite-Relative Coordinate Encoding (KT-10)

Implements approximate equivariance via bombsite-relative position encoding.
Instead of raw (x, y) normalized by map diagonal, positions are encoded as
the signed differential distance to bombsite A vs B, optionally flipped by
team side to achieve CT/T equivariance.

Reference: "Approximately Equivariant Networks" (ICLR 2026 submission)
Key insight: Penalize non-equivariance across the full group orbit via projection.
For CS2's discrete symmetries (|G| = 2), this is trivially cheap.

This module is ADDITIVE — it does NOT modify METADATA_DIM=25. Bombsite-relative
features are computed as derived values that can optionally replace pos_x/pos_y
in the feature vector via a config flag, or be used as supplementary context
in coaching analysis.

Usage:
    from Programma_CS2_RENAN.backend.processing.bombsite_encoding import (
        normalize_position_equivariant,
        get_bombsite_distances,
        MAP_BOMBSITE_CENTERS,
    )
"""

import math
from typing import Dict, Optional, Tuple

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.processing.bombsite_encoding")

# ---------------------------------------------------------------------------
# Bombsite center coordinates per active-duty map (CS2, 2024-2026 pool)
#
# Coordinates are approximate centers of each bombsite's playable area,
# derived from radar DDS textures and community callout resources.
# Format: map_name -> {"A": (x, y), "B": (x, y), "diagonal": float}
# diagonal = sqrt(map_width^2 + map_height^2) for normalization
# ---------------------------------------------------------------------------

MAP_BOMBSITE_CENTERS: Dict[str, Dict] = {
    "de_dust2": {
        "A": (-1355.0, 2485.0),
        "B": (-1220.0, 750.0),
        "diagonal": 4560.0,
    },
    "de_mirage": {
        "A": (-290.0, -2050.0),
        "B": (-2150.0, 350.0),
        "diagonal": 5200.0,
    },
    "de_inferno": {
        "A": (330.0, 360.0),
        "B": (-1950.0, 680.0),
        "diagonal": 5100.0,
    },
    "de_nuke": {
        "A": (-680.0, -390.0),
        "B": (-680.0, -770.0),  # B is below A (z-axis)
        "diagonal": 3800.0,
    },
    "de_overpass": {
        "A": (-1550.0, -400.0),
        "B": (-1730.0, 350.0),
        "diagonal": 4800.0,
    },
    "de_anubis": {
        "A": (-610.0, 890.0),
        "B": (-1880.0, -1220.0),
        "diagonal": 4600.0,
    },
    "de_vertigo": {
        "A": (-1150.0, -500.0),
        "B": (-500.0, -1100.0),
        "diagonal": 3200.0,
    },
    "de_ancient": {
        "A": (-360.0, -880.0),
        "B": (730.0, 120.0),
        "diagonal": 4400.0,
    },
    "de_train": {
        "A": (-760.0, -400.0),
        "B": (440.0, -780.0),
        "diagonal": 4200.0,
    },
}


def get_bombsite_distances(
    pos_x: float,
    pos_y: float,
    map_name: str,
) -> Optional[Tuple[float, float]]:
    """
    Compute Euclidean distance from position to each bombsite center.

    Args:
        pos_x: Player X coordinate (world units)
        pos_y: Player Y coordinate (world units)
        map_name: Map identifier (e.g. "de_dust2")

    Returns:
        (distance_to_A, distance_to_B) or None if map not in registry
    """
    info = MAP_BOMBSITE_CENTERS.get(map_name)
    if info is None:
        return None

    ax, ay = info["A"]
    bx, by = info["B"]

    dist_a = math.sqrt((pos_x - ax) ** 2 + (pos_y - ay) ** 2)
    dist_b = math.sqrt((pos_x - bx) ** 2 + (pos_y - by) ** 2)

    return dist_a, dist_b


def normalize_position_equivariant(
    pos_x: float,
    pos_y: float,
    map_name: str,
    team_side: str = "CT",
) -> float:
    """
    Compute bombsite-relative equivariant position encoding.

    Encodes position as signed differential distance: (dist_A - dist_B) / diagonal.
    CT side gets positive encoding (defending sites), T side gets negated (attacking).
    This achieves approximate equivariance under team-swap symmetry.

    Reference: KNOWLEDGE_TRANSFER Section 3.3, Eq. adapted from
    "Approximately Equivariant Networks" (ICLR 2026).

    Args:
        pos_x: Player X coordinate (world units)
        pos_y: Player Y coordinate (world units)
        map_name: Map identifier
        team_side: "CT" or "T"

    Returns:
        Normalized equivariant position scalar in [-1, 1], or 0.0 if map unknown.
    """
    info = MAP_BOMBSITE_CENTERS.get(map_name)
    if info is None:
        return 0.0

    ax, ay = info["A"]
    bx, by = info["B"]
    diagonal = info["diagonal"]

    if diagonal <= 0:
        return 0.0

    dist_a = math.sqrt((pos_x - ax) ** 2 + (pos_y - ay) ** 2)
    dist_b = math.sqrt((pos_x - bx) ** 2 + (pos_y - by) ** 2)

    normalized = (dist_a - dist_b) / diagonal

    # Equivariance: negate for T side so same physical position has
    # opposite semantic meaning for attackers vs defenders
    if team_side.upper() == "T":
        normalized = -normalized

    # Clamp to [-1, 1]
    return max(-1.0, min(1.0, normalized))


def compute_site_proximity(
    pos_x: float,
    pos_y: float,
    map_name: str,
) -> Optional[Tuple[str, float]]:
    """
    Determine which bombsite the player is closest to and the normalized distance.

    Returns:
        ("A" or "B", normalized_distance) or None if map unknown.
        normalized_distance is in [0, 1] where 0 = at site, 1 = far away.
    """
    dists = get_bombsite_distances(pos_x, pos_y, map_name)
    if dists is None:
        return None

    dist_a, dist_b = dists
    info = MAP_BOMBSITE_CENTERS[map_name]
    diagonal = info["diagonal"]

    if dist_a <= dist_b:
        return "A", min(dist_a / (diagonal * 0.5), 1.0)
    return "B", min(dist_b / (diagonal * 0.5), 1.0)
