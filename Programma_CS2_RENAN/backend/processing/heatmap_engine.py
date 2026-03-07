from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

import numpy as np
from scipy.ndimage import gaussian_filter

from Programma_CS2_RENAN.core.spatial_data import get_map_metadata

if TYPE_CHECKING:
    from kivy.graphics.texture import Texture


@dataclass
class HeatmapData:
    """Container for heatmap data that can be safely passed between threads."""

    rgba_bytes: bytes
    resolution: int


@dataclass
class DifferentialHeatmapData:
    """Container for differential heatmap data with hotspot metadata."""

    rgba_bytes: bytes
    resolution: int
    diff_matrix: np.ndarray = field(repr=False)
    hotspots: List[dict] = field(default_factory=list)


class HeatmapEngine:
    """
    High-performance Gaussian Occupancy Map generator.
    Converts discrete event points into a smooth density texture.

    THREAD SAFETY:
    - generate_heatmap_data(): Safe to call from any thread
    - create_texture_from_data(): MUST be called from the main (OpenGL) thread
    - generate_heatmap_texture(): MUST be called from the main (OpenGL) thread
    """

    @staticmethod
    def generate_heatmap_data(
        map_name: str, points: list[tuple[float, float]], resolution: int = 512, sigma: float = 8.0
    ) -> Optional[HeatmapData]:
        """
        Generates raw RGBA data for a heatmap. THREAD-SAFE.

        This method can be safely called from a background thread as it does not
        touch any OpenGL resources.

        Args:
            map_name: Name of the map (to retrieve metadata for projection).
            points: List of (x, y) tuples in World Coordinates.
            resolution: Size of the output square texture (e.g., 512x512).
            sigma: Gaussian blur intensity (smoothness).

        Returns:
            HeatmapData containing raw RGBA bytes, or None if generation failed.
        """
        if not points:
            return None

        meta = get_map_metadata(map_name)
        if not meta:
            return None

        # 1. Initialize empty grid
        # We use float32 for accumulation to prevent overflow before normalization
        grid = np.zeros((resolution, resolution), dtype=np.float32)

        # 2. Project World Points -> Grid Coordinates
        # Pre-calc constants
        scale_factor = 1.0 / (meta.scale * 1024.0)

        # Vectorized projection: world coords -> grid coords
        pts = np.asarray(points, dtype=np.float64)
        nx = (pts[:, 0] - meta.pos_x) * scale_factor
        ny = (meta.pos_y - pts[:, 1]) * scale_factor
        gx = (nx * resolution).astype(np.intp)
        gy = ((1.0 - ny) * resolution).astype(np.intp)

        # Mask out-of-bounds points
        valid = (gx >= 0) & (gx < resolution) & (gy >= 0) & (gy < resolution)
        # Atomic accumulation handles duplicate grid cells correctly
        np.add.at(grid, (gy[valid], gx[valid]), 1.0)

        # 3. Apply Gaussian Blur
        density = gaussian_filter(grid, sigma=sigma)

        # 4. Normalize (0.0 to 1.0)
        max_val = float(np.nanmax(density))
        if max_val > 0:
            density /= max_val

        # 5. Colorize (Heatmap Gradient)
        rgba = np.zeros((resolution, resolution, 4), dtype=np.uint8)

        # Red intensity style for tactical clarity
        rgba[..., 0] = 255  # Red
        rgba[..., 1] = (np.clip(1.0 - density, 0, 1) * 50).astype(np.uint8)  # Slight tint
        rgba[..., 2] = 0

        # Alpha: Non-linear ramp to hide very low values
        alpha = np.clip((density - 0.05) * 1.5, 0, 1) * 200  # Max alpha 200/255
        rgba[..., 3] = alpha.astype(np.uint8)

        return HeatmapData(rgba_bytes=rgba.tobytes(), resolution=resolution)

    @staticmethod
    def create_texture_from_data(data: HeatmapData):
        """
        Creates a Kivy Texture from pre-computed heatmap data.

        WARNING: This method MUST be called from the main (OpenGL) thread.
        Use Clock.schedule_once() to marshal this call from background threads.

        Args:
            data: HeatmapData from generate_heatmap_data()

        Returns:
            kivy.graphics.texture.Texture
        """
        from kivy.graphics.texture import Texture

        texture = Texture.create(size=(data.resolution, data.resolution), colorfmt="rgba")
        texture.blit_buffer(data.rgba_bytes, colorfmt="rgba", bufferfmt="ubyte")
        return texture

    @staticmethod
    def generate_differential_heatmap_data(
        map_name: str,
        user_positions: list[tuple[float, float]],
        pro_positions: list[tuple[float, float]],
        resolution: int = 512,
        sigma: float = 8.0,
    ) -> Optional[DifferentialHeatmapData]:
        """
        Generates differential heatmap RGBA data comparing user vs pro positions.
        THREAD-SAFE — does not touch OpenGL resources.

        Uses KDE (Gaussian blur) to compute density grids for both sets,
        normalizes each to [0, 1], then subtracts: ``pro_density - user_density``.
        Applies a diverging colormap: blue = user-heavy, red = pro-heavy,
        white/transparent = equal density.

        Also extracts hotspot regions where the biggest differences occur,
        for downstream coaching integration.

        Args:
            map_name: CS2 map identifier for coordinate projection.
            user_positions: (x, y) world-coordinate tuples for the user.
            pro_positions: (x, y) world-coordinate tuples for pro players.
            resolution: Square texture resolution.
            sigma: Gaussian blur intensity.

        Returns:
            DifferentialHeatmapData with RGBA bytes, diff matrix, and hotspots,
            or None if insufficient data.
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
            ny = (meta.pos_y - pts[:, 1]) * scale_factor
            gx = (nx * resolution).astype(np.intp)
            gy = ((1.0 - ny) * resolution).astype(np.intp)
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

        # Colorize with diverging scheme: blue ← white → red
        rgba = np.zeros((resolution, resolution, 4), dtype=np.uint8)

        # Clamp diff to [-1, 1]
        clamped = np.clip(diff, -1.0, 1.0)

        # Red channel: stronger where pro-heavy (positive diff)
        pro_strength = np.clip(clamped, 0.0, 1.0)
        # Blue channel: stronger where user-heavy (negative diff)
        user_strength = np.clip(-clamped, 0.0, 1.0)

        rgba[..., 0] = (pro_strength * 255).astype(np.uint8)  # Red = pro-heavy
        rgba[..., 1] = 0  # No green
        rgba[..., 2] = (user_strength * 255).astype(np.uint8)  # Blue = user-heavy

        # Alpha: proportional to absolute difference, masked by activity
        abs_diff = np.abs(clamped)
        alpha = np.clip(abs_diff * 2.0, 0, 1) * 180  # Max alpha 180/255
        alpha[~activity] = 0
        rgba[..., 3] = alpha.astype(np.uint8)

        # Extract hotspots: regions with largest absolute difference
        hotspots = HeatmapEngine._extract_hotspots(diff, activity, meta, resolution)

        return DifferentialHeatmapData(
            rgba_bytes=rgba.tobytes(),
            resolution=resolution,
            diff_matrix=diff,
            hotspots=hotspots,
        )

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

            # Reverse project: grid → world
            nx = gx / resolution
            ny = 1.0 - (gy / resolution)
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

    @staticmethod
    def generate_heatmap_texture(
        map_name: str, points: list[tuple[float, float]], resolution: int = 512, sigma: float = 8.0
    ):
        """
        Generates a RGBA texture representing the heatmap density.

        WARNING: This method MUST be called from the main (OpenGL) thread.
        For background thread usage, use generate_heatmap_data() followed by
        Clock.schedule_once() + create_texture_from_data().

        Args:
            map_name: Name of the map (to retrieve metadata for projection).
            points: List of (x, y) tuples in World Coordinates.
            resolution: Size of the output square texture (e.g., 512x512).
            sigma: Gaussian blur intensity (smoothness).

        Returns:
            kivy.graphics.texture.Texture or None
        """
        data = HeatmapEngine.generate_heatmap_data(map_name, points, resolution, sigma)
        if data is None:
            return None
        return HeatmapEngine.create_texture_from_data(data)
