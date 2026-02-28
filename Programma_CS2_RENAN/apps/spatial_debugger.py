from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line
from kivy.properties import BooleanProperty, ObjectProperty, StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from Programma_CS2_RENAN.core.asset_manager import AssetAuthority
from Programma_CS2_RENAN.core.spatial_data import LANDMARKS, get_map_metadata


class SpatialValidatorWidget(FloatLayout):
    """
    Debug widget for validating Spatial Engine accuracy (Phase 1, 20%).

    Features:
    - Real-time Cursor-to-World coordinate translation.
    - Visualization of known landmarks (Spawn points, Sites) for alignment checking.
    - 'Ghost Pixel' crosshair tracking.
    """

    map_name = StringProperty("de_mirage")
    is_active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Background Map Image
        self.map_image = Image(
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self.add_widget(self.map_image)

        # Debug Info Label (Top Left)
        self.info_label = Label(
            text="SPATIAL DEBUGGER: INACTIVE",
            size_hint=(None, None),
            size=(400, 100),
            pos_hint={"x": 0, "top": 1},
            halign="left",
            valign="top",
            color=(0, 1, 0, 1),  # Green terminal style
            outline_color=(0, 0, 0, 1),
            outline_width=2,
        )
        self.info_label.bind(size=self.info_label.setter("text_size"))
        self.add_widget(self.info_label)

        # Trigger initial load
        self.bind(map_name=self.load_map)
        self.load_map()

    def load_map(self, *args):
        """Loads the map image using the Asset Authority."""
        asset = AssetAuthority.get_map_asset(self.map_name)
        if asset.is_fallback:
            self.map_image.texture = asset.texture
        else:
            self.map_image.source = asset.path

        self.draw_landmarks()

    def on_touch_down(self, touch):
        if not self.is_active:
            return super().on_touch_down(touch)
        if self.map_image.collide_point(*touch.pos):
            self.update_debug_info(touch)
            return True  # Consume touch
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if not self.is_active:
            return super().on_touch_move(touch)
        if self.map_image.collide_point(*touch.pos):
            self.update_debug_info(touch)
            return True
        return super().on_touch_move(touch)

    def update_debug_info(self, touch):
        """Calculates World Coordinates from UI Touch."""
        # 1. Get relative coordinates within the image widget
        # The image might be letterboxed, so we need the actual texture position
        norm_x = (touch.x - self.map_image.x) / self.map_image.width
        norm_y = (touch.y - self.map_image.y) / self.map_image.height

        # Note: Kivy Image 'norm_image_x' etc is tricky with keep_ratio.
        # For a truly accurate validator, we assume the image fills the widget
        # or we calculate the actual image ratio offset.
        # For this prototype, we assume the widget IS the map area (simple validation).

        metadata = get_map_metadata(self.map_name)
        if not metadata:
            self.info_label.text = f"UNKNOWN MAP: {self.map_name}"
            return

        # Y is inverted in Kivy (Bottom-Left 0,0) vs Radar Image (Top-Left 0,0 usually?)
        # Standard Radar images: Top-Left is (0,0).
        # Kivy Touch: Bottom-Left is (0,0).
        # So Radar Y = 1.0 - Kivy Y
        radar_norm_y = 1.0 - norm_y

        world_x, world_y = metadata.radar_to_world(norm_x, radar_norm_y)

        self.info_label.text = (
            f"MAP: {self.map_name}\n"
            f"UI POS: {int(touch.x)}, {int(touch.y)}\n"
            f"NORM: {norm_x:.3f}, {radar_norm_y:.3f}\n"
            f"WORLD: X={world_x:.1f}, Y={world_y:.1f}"
        )

        # Draw Ghost Crosshair
        self.canvas.after.clear()
        with self.canvas.after:
            Color(1, 0, 0, 0.8)  # Red
            size = 10
            Line(points=[touch.x - size, touch.y, touch.x + size, touch.y], width=1.5)
            Line(points=[touch.x, touch.y - size, touch.x, touch.y + size], width=1.5)

    def draw_landmarks(self):
        """Draws known landmarks (Spawn, Sites) on the map for visual alignment check."""
        self.canvas.before.clear()

        metadata = get_map_metadata(self.map_name)
        if not metadata or self.map_name not in LANDMARKS:
            return

        points = LANDMARKS[self.map_name]

        with self.canvas.before:
            for name, (wx, wy) in points.items():
                # Convert World -> Radar -> UI
                # 1. World -> Radar Norm
                rn_x, rn_y = metadata.world_to_radar(wx, wy)

                # 2. Radar Norm -> UI Norm (Flip Y back for Kivy)
                ui_nx = rn_x
                ui_ny = 1.0 - rn_y

                # 3. UI Norm -> Screen Pixel
                px = self.map_image.x + (ui_nx * self.map_image.width)
                py = self.map_image.y + (ui_ny * self.map_image.height)

                # Draw
                Color(0, 1, 1, 1)  # Cyan
                Ellipse(pos=(px - 5, py - 5), size=(10, 10))
