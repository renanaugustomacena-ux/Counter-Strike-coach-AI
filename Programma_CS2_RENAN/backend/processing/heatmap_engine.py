from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from scipy.ndimage import gaussian_filter

from Programma_CS2_RENAN.core.spatial_data import get_map_metadata


@dataclass
class DifferentialHeatmapData:
    """Container for differential heatmap hotspot metadata.

    F-0017: the RGBA texture surface (rgba_bytes / diff_matrix and the whole
    Kivy texture path) had zero consumers and carried a Kivy-era double
    Y-flip; it was removed. The sole production consumer
    (coaching_service.generate_differential_insights) reads .hotspots.
    (Law I repair: the comment previously named a method that never existed.)
    """

    resolution: int
    hotspots: List[dict] = field(default_factory=list)


class HeatmapEngine:
    """
    Gaussian occupancy comparison between user and pro positions.

    Grid convention (C-03, same as tensor_factory._world_to_grid): a SINGLE
    Y-flip — ``ny = (meta.pos_y - world_y) * scale`` then ``gy = ny * res``.
    Row 0 is the map's north edge.

    THREAD SAFETY: generate_differential_heatmap_data() is safe to call from
    any thread (pure numpy, no GUI resources).
    """

    @staticmethod
    def generate_differential_heatmap_data(
        map_name: str,
        user_positions: list[tuple[float, float]],
        pro_positions: list[tuple[float, float]],
        resolution: int = 512,
        sigma: float = 8.0,
    ) -> Optional[DifferentialHeatmapData]:
        """
        Compares user vs pro positional density and extracts hotspots.
        THREAD-SAFE — does not touch GUI resources.

        Uses KDE (Gaussian blur) to compute density grids for both sets,
        normalizes each to [0, 1], then subtracts: ``pro_density -
        user_density``. Hotspot regions with the biggest differences are
        returned in world coordinates for coaching integration.

        Args:
            map_name: CS2 map identifier for coordinate projection.
            user_positions: (x, y) world-coordinate tuples for the user.
            pro_positions: (x, y) world-coordinate tuples for pro players.
            resolution: Square grid resolution.
            sigma: Gaussian blur intensity.

        Returns:
            DifferentialHeatmapData with hotspots, or None if insufficient
            data.
        """
        if not user_positions or not pro_positions:
            return None

        meta = get_map_metadata(map_name)
        if not meta:
            return None

        scale_factor = 1.0 / (meta.scale * 1024.0)

        def _positions_to_grid(positions: list[tuple[float, float]]) -> np.ndarray:
            grid = np.zeros((resolution, resolution), dtype=np.float32)
            pts = np.asarray(positions, dtype=np.float64)
            nx = (pts[:, 0] - meta.pos_x) * scale_factor
            # C-03: single Y-flip only (meta.pos_y - y already inverts).
            ny = (meta.pos_y - pts[:, 1]) * scale_factor
            gx = (nx * resolution).astype(np.intp)
            gy = (ny * resolution).astype(np.intp)
            valid = (gx >= 0) & (gx < resolution) & (gy >= 0) & (gy < resolution)
            np.add.at(grid, (gy[valid], gx[valid]), 1.0)
            density = gaussian_filter(grid, sigma=sigma)
            max_val = np.max(density)
            if max_val > 0:
                density /= max_val
            return density

        d_user = _positions_to_grid(user_positions)
        d_pro = _positions_to_grid(pro_positions)

        # Difference: positive = pro-heavy, negative = user-heavy
        diff = d_pro - d_user

        # Activity mask — suppress noise in empty areas
        activity = (d_user > 0.02) | (d_pro > 0.02)

        hotspots = HeatmapEngine._extract_hotspots(diff, activity, meta, resolution)

        return DifferentialHeatmapData(resolution=resolution, hotspots=hotspots)

    @staticmethod
    def _extract_hotspots(
        diff: np.ndarray,
        activity: np.ndarray,
        meta,
        resolution: int,
        top_n: int = 5,
    ) -> List[dict]:
        """
        Identifies the top-N grid cells with the largest absolute difference,
        and converts grid coordinates back to approximate world coordinates.
        """
        masked = np.where(activity, diff, 0.0)
        abs_masked = np.abs(masked)

        # Flatten, sort descending, pick top-N
        flat_indices = np.argsort(abs_masked.ravel())[::-1][:top_n]

        scale_factor = 1.0 / (meta.scale * 1024.0)
        inv_scale = 1.0 / scale_factor if scale_factor != 0 else 1.0

        hotspots = []
        for idx in flat_indices:
            gy, gx = divmod(idx, resolution)
            val = diff[gy, gx]
            if abs(val) < 0.05:
                continue  # Skip negligible spots

            # Reverse project: grid → world (inverse of the single-flip
            # forward projection above — round-trip identity).
            nx = gx / resolution
            ny = gy / resolution
            wx = nx * inv_scale + meta.pos_x
            wy = meta.pos_y - ny * inv_scale

            hotspots.append(
                {
                    "world_x": float(wx),
                    "world_y": float(wy),
                    "diff_value": float(val),
                    "label": "pro-heavy" if val > 0 else "user-heavy",
                    "magnitude": float(abs(val)),
                }
            )

        return hotspots
