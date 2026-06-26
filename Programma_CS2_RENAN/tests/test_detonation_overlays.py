"""
Detonation Radius Overlays Tests

Validates the CS2 grenade detonation overlay constants and integration in the
ACTIVE Qt tactical map (apps/qt_app/widgets/tactical/map_widget.py).

History: these constants originally lived in the legacy Kivy TacticalMap. That
UI was migrated to PySide6/Qt and the legacy package removed; the Qt map_widget
owns the production constants now (identical CS2 game values), so this test was
repointed at the live module. The constant checks now actually run (they were
skipped while the source-of-truth was the never-imported Kivy module).

Validates:
- Grenade radius constants are correct CS2 game values
- Overlay colors are defined for all grenade types
- _draw_detonation_overlay exists and is wired into nade drawing
"""

import os

import pytest

from Programma_CS2_RENAN.core.demo_frame import NadeType

# Importing the Qt widget module only defines the class + module-level constant
# dicts (no QApplication needed). Guard so the suite still degrades gracefully
# on an environment without PySide6 installed.
try:
    from PySide6.QtGui import QColor

    from Programma_CS2_RENAN.apps.qt_app.widgets.tactical.map_widget import (
        GRENADE_OVERLAY_COLORS,
        GRENADE_RADII,
    )

    _QT_AVAILABLE = True
except Exception:  # pragma: no cover - only on a Qt-less environment
    _QT_AVAILABLE = False

_QT_SOURCE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "apps",
    "qt_app",
    "widgets",
    "tactical",
    "map_widget.py",
)

pytestmark = pytest.mark.skipif(
    not _QT_AVAILABLE, reason="PySide6 not available — cannot import Qt map_widget"
)


class TestGrenadeConstants:
    """Verify CS2 grenade radius constants and overlay colors from production."""

    def test_all_nade_types_have_radii(self):
        """Every NadeType should have a defined radius in production constants."""
        expected_types = [NadeType.HE, NadeType.MOLOTOV, NadeType.SMOKE, NadeType.FLASH]
        for nt in expected_types:
            assert nt in GRENADE_RADII, f"{nt} missing from GRENADE_RADII"

    def test_radius_values_match_cs2_game_data(self):
        """Radius values must match known CS2 game constants."""
        assert GRENADE_RADII[NadeType.HE] == 350
        assert GRENADE_RADII[NadeType.MOLOTOV] == 180
        assert GRENADE_RADII[NadeType.SMOKE] == 144
        assert GRENADE_RADII[NadeType.FLASH] == 1000

    def test_radius_values_are_positive(self):
        """All radius values must be positive."""
        for nade_type, radius in GRENADE_RADII.items():
            assert radius > 0, f"{nade_type} has non-positive radius: {radius}"

    def test_overlay_colors_defined_for_all_types(self):
        """Every NadeType with a radius must have an overlay color."""
        for nade_type in GRENADE_RADII:
            assert (
                nade_type in GRENADE_OVERLAY_COLORS
            ), f"{nade_type} missing from GRENADE_OVERLAY_COLORS"

    def test_overlay_colors_are_valid_qcolors(self):
        """Overlay colors must be QColor instances with in-range RGB channels."""
        for nade_type, color in GRENADE_OVERLAY_COLORS.items():
            assert isinstance(color, QColor), f"{nade_type} color is not a QColor"
            for channel in (color.red(), color.green(), color.blue()):
                assert 0 <= channel <= 255, f"{nade_type} channel {channel} out of [0, 255]"


class TestTacticalMapOverlayIntegration:
    """Verify the detonation overlay is defined and wired into the Qt map source."""

    @staticmethod
    def _source() -> str:
        with open(_QT_SOURCE, "r", encoding="utf-8") as f:
            return f.read()

    def test_constants_defined_in_source(self):
        """map_widget source must define the grenade overlay constants."""
        source = self._source()
        assert "GRENADE_RADII" in source
        assert "GRENADE_OVERLAY_COLORS" in source

    def test_draw_detonation_overlay_method_exists(self):
        """_draw_detonation_overlay must be defined in map_widget.py."""
        assert "def _draw_detonation_overlay" in self._source()

    def test_overlay_integrated_in_nade_drawing(self):
        """_draw_detonation_overlay must be called from the nade-drawing path."""
        source = self._source()
        # Definition plus at least one call site.
        assert source.count("_draw_detonation_overlay") >= 2
