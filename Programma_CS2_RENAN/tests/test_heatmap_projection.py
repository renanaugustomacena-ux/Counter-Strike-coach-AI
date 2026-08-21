"""F-0017 — heatmap grid follows the C-03 single-Y-flip convention and the
hotspot reverse projection round-trips world coordinates."""

from types import SimpleNamespace

import pytest

from Programma_CS2_RENAN.backend.processing import heatmap_engine as he

# Radar-style metadata: origin at the NW corner, 4096 world units per side.
_META = SimpleNamespace(pos_x=-2000.0, pos_y=2000.0, scale=4.0)
_SPAN = _META.scale * 1024.0  # 4096.0


@pytest.fixture
def fake_meta(monkeypatch):
    monkeypatch.setattr(he, "get_map_metadata", lambda name: _META)
    return _META


def _cluster(x, y, n=50):
    return [(x, y)] * n


class TestSingleFlipConvention:
    def test_matches_tensor_factory_row_band(self, fake_meta):
        """A world point near the north edge (y ≈ pos_y) must land in the TOP
        rows — the same convention as tensor_factory._world_to_grid (C-03)."""
        from Programma_CS2_RENAN.backend.processing.tensor_factory import TensorFactory

        res = 64
        north_point = (-1000.0, 1800.0)  # y close to pos_y → north
        south_point = (-1000.0, -1800.0)

        tf = TensorFactory()
        _, gy_north = tf._world_to_grid(north_point[0], north_point[1], _META, res)
        _, gy_south = tf._world_to_grid(south_point[0], south_point[1], _META, res)
        assert gy_north < res / 2 < gy_south  # sanity on the doctrine itself

        data = he.HeatmapEngine.generate_differential_heatmap_data(
            "de_test",
            user_positions=_cluster(*south_point),
            pro_positions=_cluster(*north_point),
            resolution=res,
            sigma=1.0,
        )
        pro_spot = next(h for h in data.hotspots if h["label"] == "pro-heavy")
        user_spot = next(h for h in data.hotspots if h["label"] == "user-heavy")
        # Pro cluster sits north → its hotspot world_y must be the northern one.
        assert pro_spot["world_y"] > user_spot["world_y"]

    def test_hotspot_world_roundtrip(self, fake_meta):
        """Hotspots must land within a couple of grid cells of the true world
        position of the density cluster (round-trip identity)."""
        res = 64
        cell = _SPAN / res
        pro_at = (500.0, -750.0)
        user_at = (-1500.0, 1500.0)

        data = he.HeatmapEngine.generate_differential_heatmap_data(
            "de_test",
            user_positions=_cluster(*user_at),
            pro_positions=_cluster(*pro_at),
            resolution=res,
            sigma=1.0,
        )
        pro_spot = next(h for h in data.hotspots if h["label"] == "pro-heavy")
        assert abs(pro_spot["world_x"] - pro_at[0]) <= 2 * cell
        assert abs(pro_spot["world_y"] - pro_at[1]) <= 2 * cell

    def test_dead_kivy_surface_removed(self):
        assert not hasattr(he, "HeatmapData")
        assert not hasattr(he.HeatmapEngine, "generate_heatmap_data")
        assert not hasattr(he.HeatmapEngine, "create_texture_from_data")
        assert not hasattr(he.HeatmapEngine, "generate_heatmap_texture")
