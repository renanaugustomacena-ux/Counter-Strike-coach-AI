from typing import Tuple

from Programma_CS2_RENAN.core.spatial_data import get_map_metadata

# Must match the default radar_width in MapMetadata.world_to_radar()
RADAR_REFERENCE_SIZE = 1024.0


class SpatialEngine:
    """
    Core engine for handling coordinate transformations between
    Game World (Source Engine units) and UI/Pixel space.
    """

    @staticmethod
    def world_to_normalized(x: float, y: float, map_name: str) -> Tuple[float, float]:
        """
        Convert world coordinates to normalized (0.0 - 1.0) space.
        """
        meta = get_map_metadata(map_name)
        if not meta:
            return 0.5, 0.5
        return meta.world_to_radar(x, y)

    @staticmethod
    def normalized_to_pixel(
        nx: float, ny: float, viewport_w: float, viewport_h: float
    ) -> Tuple[float, float]:
        """
        Convert normalized coordinates to specific viewport pixel coordinates.
        """
        return nx * viewport_w, ny * viewport_h

    @staticmethod
    def pixel_to_normalized(
        px: float, py: float, viewport_w: float, viewport_h: float
    ) -> Tuple[float, float]:
        """
        Convert viewport pixel coordinates to normalized space.
        """
        if viewport_w == 0 or viewport_h == 0:
            return 0.0, 0.0
        return px / viewport_w, py / viewport_h

    @staticmethod
    def world_to_pixel(
        x: float, y: float, map_name: str, viewport_w: float, viewport_h: float
    ) -> Tuple[float, float]:
        """
        Direct world-to-pixel conversion.
        """
        nx, ny = SpatialEngine.world_to_normalized(x, y, map_name)
        # Note: Kivy Y is inverted relative to standard image coordinates (0,0 is bottom-left)
        # But world_to_radar returns coordinates relative to image top-left (usually).
        # We need to handle the Y-flip at the rendering layer (TacticalMap) or here.
        # TacticalMap._world_to_screen handles the flip:
        # return (self.x + nx * map_size + offset_x, self.y + (1.0 - ny) * map_size + offset_y)
        # So here we just return the raw projection.
        return SpatialEngine.normalized_to_pixel(nx, ny, viewport_w, viewport_h)

    @staticmethod
    def pixel_to_world(
        px: float, py: float, map_name: str, viewport_w: float, viewport_h: float
    ) -> Tuple[float, float]:
        """
        Direct pixel-to-world conversion (Inverse of world_to_pixel).
        """
        nx, ny = SpatialEngine.pixel_to_normalized(px, py, viewport_w, viewport_h)

        meta = get_map_metadata(map_name)
        if not meta:
            return 0.0, 0.0

        # Inverse logic needs to match spatial_data.py
        # norm_x = pixel_x / RADAR_REFERENCE_SIZE
        # pixel_x = (x - pos_x) / scale
        # => nx = (x - pos_x) / (scale * RADAR_REFERENCE_SIZE)
        # => x = nx * scale * RADAR_REFERENCE_SIZE + pos_x

        # pixel_y = (pos_y - y) / scale
        # ny = pixel_y / RADAR_REFERENCE_SIZE
        # => ny = (pos_y - y) / (scale * RADAR_REFERENCE_SIZE)
        # => y = pos_y - (ny * scale * RADAR_REFERENCE_SIZE)

        w_x = nx * (meta.scale * RADAR_REFERENCE_SIZE) + meta.pos_x
        w_y = meta.pos_y - (ny * (meta.scale * RADAR_REFERENCE_SIZE))

        return w_x, w_y
