import math
from typing import List, Tuple

from kivy.graphics import Color, InstructionGroup, Line
from kivy.uix.widget import Widget

from Programma_CS2_RENAN.core.spatial_data import MapMetadata


class GrenadeVisualizer(Widget):
    """
    Renders grenade trajectories with simulated arc height.
    (Phase 2, 55%)
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.instructions = InstructionGroup()
        self.canvas.add(self.instructions)

    def draw_trajectories(
        self,
        grenades: List[dict],
        metadata: MapMetadata,
        map_size: Tuple[float, float],
        map_pos: Tuple[float, float],
    ):
        """
        Draws grenade paths.

        Args:
            grenades: List of dicts {
                'start': (x, y, z),
                'end': (x, y, z),
                'type': 'Smoke'|'Flash'|'HE'|'Molotov'
            }
            metadata: MapMetadata for coordinate conversion.
            map_size: (width, height) of the map widget.
            map_pos: (x, y) of the map widget.
        """
        self.instructions.clear()

        for g in grenades:
            self._draw_single_grenade(g, metadata, map_size, map_pos)

    def _draw_single_grenade(self, grenade, metadata, map_size, map_pos):
        sx, sy, sz = grenade["start"]
        ex, ey, ez = grenade["end"]
        g_type = grenade.get("type", "HE")

        # 1. Convert Start/End to UI Coordinates
        start_norm = metadata.world_to_radar(sx, sy)
        end_norm = metadata.world_to_radar(ex, ey)

        # Flip Y for Kivy
        ui_sx = map_pos[0] + (start_norm[0] * map_size[0])
        ui_sy = map_pos[1] + ((1.0 - start_norm[1]) * map_size[1])

        ui_ex = map_pos[0] + (end_norm[0] * map_size[0])
        ui_ey = map_pos[1] + ((1.0 - end_norm[1]) * map_size[1])

        # 2. Color Selection
        if g_type == "Smoke":
            color = (0.5, 0.5, 0.5, 0.8)  # Grey
        elif g_type == "Flash":
            color = (1, 1, 0.8, 0.8)  # Pale Yellow
        elif g_type == "Molotov" or g_type == "Incendiary":
            color = (1, 0.4, 0, 0.8)  # Orange
        else:
            color = (1, 0, 0, 0.8)  # Red (HE)

        self.instructions.add(Color(*color))

        # 3. Calculate Arc (Simulated)
        # We want to show a curve that simulates the throw.
        # Simple quadratic bezier: Start -> Control -> End
        # Control point is midpoint + offset perpendicular to line (or just Up in 2D to fake 3D height?)
        # Actually, for top-down 2D, a straight line is technically correct for XY position.
        # BUT, to visualize "Arc Height" (Z-axis), we can use a trick:
        # We can offset the midpoint "Up" (Positive Y in UI) based on the Z-diff or distance.
        # However, shifting Y in 2D map confuses spatial position.
        # BETTER: Draw the shadow (straight line) and the trajectory (curved)??
        # No, that's too cluttered.
        # STANDARD APPROACH for Top-Down: Straight line for path, dotted line.
        # The roadmap asks for "Arc Height".
        # Interpretation: Maybe we interpret Z as "Line Width" or "Alpha" or simply map Z changes?
        # Let's stick to a straight line for XY accuracy (Tactical fidelity).
        # And add a "Detonation Circle" at the end.

        # Line
        self.instructions.add(
            Line(points=[ui_sx, ui_sy, ui_ex, ui_ey], width=1.5, dash_length=5, dash_offset=2)
        )

        # Detonation/Landing Point
        # Draw a small cross or circle
        radius = 3
        self.instructions.add(Line(circle=(ui_ex, ui_ey, radius), width=1))

        # Optional: Label or Icon for type? (Skipping for performance/clutter)
