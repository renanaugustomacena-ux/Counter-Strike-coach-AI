from typing import List, Tuple

import numpy as np
import scipy.ndimage
from kivy.graphics.texture import Texture

from Programma_CS2_RENAN.core.spatial_data import MapMetadata


class HeatmapEngine:
    """
    High-Performance Gaussian Occupancy Map Generator (Phase 2, 40%).
    Uses numpy and scipy for off-thread calculation of density maps.
    """

    def __init__(self, radar_size: int = 512, sigma: float = 8.0):
        """
        Args:
            radar_size: Internal resolution of the heatmap grid (default 512x512).
                        Lower values = faster generation, softer look.
            sigma: Standard deviation for Gaussian kernel (spread of heat).
        """
        self.radar_size = radar_size
        self.sigma = sigma
        self.grid = np.zeros((radar_size, radar_size), dtype=np.float32)

        # Pre-compute colormap (Blue -> Green -> Red)
        # We'll use a simple LUT (Look Up Table) for performance
        self.colormap = self._generate_colormap()

    def _generate_colormap(self) -> np.ndarray:
        """Generates a 256x3 RGB lookup table."""
        # Simple Thermal Gradient: Blue(0) -> Cyan(0.33) -> Yellow(0.66) -> Red(1.0)
        # Using interpolation for simplicity
        x = np.linspace(0, 1, 256)

        # Red channel
        r = np.interp(x, [0, 0.33, 0.66, 1], [0, 0, 1, 1])
        # Green channel
        g = np.interp(x, [0, 0.33, 0.66, 1], [0, 1, 1, 0])
        # Blue channel
        b = np.interp(x, [0, 0.33, 0.66, 1], [1, 1, 0, 0])

        # Stack and scale to 0-255
        cmap = np.dstack((r, g, b))[0] * 255
        return cmap.astype(np.uint8)

    def generate_texture(
        self, player_positions: List[Tuple[float, float]], metadata: MapMetadata
    ) -> Texture:
        """
        Converts a list of World (X, Y) coordinates into a Kivy Texture.

        Args:
            player_positions: List of (x, y) tuples in Source 2 World Coords.
            metadata: MapMetadata for coordinate translation.

        Returns:
            Kivy Texture object containing the heatmap (RGBA).
        """
        # 1. Reset Grid
        self.grid.fill(0)

        if not player_positions:
            return self._empty_texture()

        # 2. Map World -> Grid Coordinates
        # Vectorized operation would be better, but loop is fine for < 100 points (10 players * 10 ticks history)
        # Optimization: Use numpy for batch conversion if list is massive

        pts = np.array(player_positions)
        if pts.shape[0] > 0:
            # Vectorized World -> Radar Norm
            # Formula: norm_x = ((x - pos_x) / scale) / radar_width
            # But we want Grid Coords directly:
            # grid_x = ((x - pos_x) / scale) * (grid_size / radar_width_ref)
            # Assuming radar_width_ref usually 1024, but strictly we just map 0.0-1.0 to 0-grid_size

            # MapMetadata.world_to_radar returns 0.0-1.0
            # We assume a reference width for world_to_radar doesn't matter as long as output is norm
            # But world_to_radar takes 'radar_width'. Let's use 1.0 to get normalized.

            # Unpack metadata
            pos_x = metadata.pos_x
            pos_y = metadata.pos_y
            scale = metadata.scale

            # Calculate pixel offsets in standard scale
            pixel_x = (pts[:, 0] - pos_x) / scale
            pixel_y = (pos_y - pts[:, 1]) / scale  # Inverted Y

            # Normalize to 0-1 (Assuming 1024 width standard for scale factors provided)
            # The scale factors in spatial_data.py are calibrated for 1024x1024 images.
            norm_x = pixel_x / 1024.0
            norm_y = pixel_y / 1024.0

            # Scale to internal grid size
            gx = (norm_x * self.radar_size).astype(int)
            gy = (norm_y * self.radar_size).astype(int)

            # Filter out of bounds
            mask = (gx >= 0) & (gx < self.radar_size) & (gy >= 0) & (gy < self.radar_size)
            gx = gx[mask]
            gy = gy[mask]

            # 3. Accumulate Density
            # np.add.at is fast unbuffered in-place add
            np.add.at(self.grid, (gy, gx), 1.0)

        # 4. Apply Gaussian Smoothing (The "Heat" effect)
        # This is the heavy op. On 512x512 it takes ~5-15ms depending on CPU.
        smoothed = scipy.ndimage.gaussian_filter(self.grid, sigma=self.sigma)

        # 5. Normalize (Scale to 0-1 range for mapping)
        max_val = np.max(smoothed)
        if max_val > 0:
            smoothed /= max_val

        # 6. Apply Colormap & Create RGBA Buffer
        # Map 0.0-1.0 float to 0-255 int indices
        indices = (smoothed * 255).astype(np.uint8)

        # Lookup RGB
        rgb = self.colormap[indices]

        # Create Alpha channel: Transparent where density is low
        # Alpha ramp: 0->0, 0.1->0.5, 1.0->0.9
        alpha = (smoothed * 255).astype(np.uint8)
        alpha = np.expand_dims(alpha, axis=-1)

        # Stack RGBA
        rgba = np.dstack((rgb, alpha)).astype(np.uint8)

        # 7. Create Kivy Texture
        # Note: Kivy textures are usually flipped vertically vs numpy arrays
        # We might need to flip buffer. Kivy expects Bottom-to-Top.
        # Numpy (Image) is usually Top-to-Bottom.
        # However, our world_to_radar mapped Y to top-down pixel coords.
        # So we probably need to flip to match Kivy's coordinate system.
        rgba = np.flipud(rgba)

        buf = rgba.tobytes()
        texture = Texture.create(size=(self.radar_size, self.radar_size), colorfmt="rgba")
        texture.blit_buffer(buf, colorfmt="rgba", bufferfmt="ubyte")

        return texture

    def _empty_texture(self):
        """Returns a transparent texture."""
        texture = Texture.create(size=(self.radar_size, self.radar_size), colorfmt="rgba")
        # Empty buffer
        return texture
