"""
Detonation Radius Overlays Tests

Validates the CS2 grenade detonation overlay constants and integration in the
ACTIVE Qt tactical map (apps/qt_app/widgets/tactical/map_widget.py).

History: these constants originally lived in the legacy Kivy TacticalMap. That
UI was migrated to PySide6/Qt and the legacy package removed; the Qt map_widget
owns the production constants now (identical CS2 game values), so this test was
repointed at the live module. Overlay colors then moved from a module-level
QColor dict to design tokens: _NADE_PALETTE_KEYS maps each NadeType to a
semantic palette key resolved by TacticalMapWidget._palette() per paint, so
overlays theme-track (CS2 / CSGO / CS1.6).

Validates:
- Grenade radius constants are correct CS2 game values
- Every grenade type maps to a token-palette color
- _draw_detonation_overlay exists and is wired into nade drawing
"""

import os

import pytest

from Programma_CS2_RENAN.core.demo_frame import NadeType

# Must be set BEFORE any QApplication is created — enables headless CI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Guard so the suite still degrades gracefully on an environment without
# PySide6 installed.
try:
    from PySide6.QtGui import QColor

    from Programma_CS2_RENAN.apps.qt_app.widgets.tactical.map_widget import (
        _NADE_PALETTE_KEYS,
        GRENADE_RADII,
        TacticalMapWidget,
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


@pytest.fixture(scope="module")
def qapp():
    """Provide a QApplication so TacticalMapWidget can be constructed."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


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
        """Every NadeType with a radius must map to a palette key."""
        for nade_type in GRENADE_RADII:
            assert nade_type in _NADE_PALETTE_KEYS, f"{nade_type} missing from _NADE_PALETTE_KEYS"

    def test_overlay_colors_are_valid_qcolors(self, qapp):
        """Palette colors for every grenade type must be valid QColors."""
        widget = TacticalMapWidget()
        palette = widget._palette()
        for nade_type, key in _NADE_PALETTE_KEYS.items():
            assert key in palette, f"{nade_type} key {key!r} missing from _palette()"
            color = palette[key]
            assert isinstance(color, QColor), f"{nade_type} color is not a QColor"
            for channel in (color.red(), color.green(), color.blue()):
                assert 0 <= channel <= 255, f"{nade_type} channel {channel} out of [0, 255]"
        widget.deleteLater()


class TestTacticalMapOverlayIntegration:
    """Verify the detonation overlay is defined and wired into the Qt map source."""

    @staticmethod
    def _source() -> str:
        with open(_QT_SOURCE, "r", encoding="utf-8") as f:
            return f.read()

    def test_constants_defined_in_source(self):
        """map_widget source must define the grenade radius + palette maps."""
        source = self._source()
        assert "GRENADE_RADII" in source
        assert "_NADE_PALETTE_KEYS" in source

    def test_draw_detonation_overlay_method_exists(self):
        """_draw_detonation_overlay must be defined in map_widget.py."""
        assert "def _draw_detonation_overlay" in self._source()

    def test_overlay_integrated_in_nade_drawing(self):
        """_draw_detonation_overlay must be called from the nade-drawing path."""
        source = self._source()
        # Definition plus at least one call site.
        assert source.count("_draw_detonation_overlay") >= 2
