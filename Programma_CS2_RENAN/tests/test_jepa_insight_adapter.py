"""F1.1 (W5.1) — JEPA insight adapter tests.

Pure-function coverage of the delta→insight mapping (axis vocabulary,
maturity ladder, noise threshold, direction semantics) plus the loader's
26-HYB-01 discipline (weights-or-None) and the setting gate.
"""

from __future__ import annotations

from unittest import mock

import pytest


def _outputs(**overrides):
    """Neutral sigmoid outputs (0.5 == zero delta) with named overrides."""
    from Programma_CS2_RENAN.backend.coaching.jepa_insight_adapter import _TARGET_FEATURES

    base = {f: 0.5 for f in _TARGET_FEATURES}
    base.update(overrides)
    return [base[f] for f in _TARGET_FEATURES]


class TestDeltasToInsights:
    def test_neutral_outputs_yield_nothing(self):
        from Programma_CS2_RENAN.backend.coaching.jepa_insight_adapter import deltas_to_insights

        assert deltas_to_insights(_outputs(), "mature") == []

    def test_sub_threshold_noise_is_dropped(self):
        from Programma_CS2_RENAN.backend.coaching.jepa_insight_adapter import deltas_to_insights

        # |2*(0.54-0.5)| = 0.08 < 0.1 threshold
        assert deltas_to_insights(_outputs(health=0.54), "mature") == []

    def test_strong_delta_maps_axis_and_direction(self):
        from Programma_CS2_RENAN.backend.coaching.jepa_insight_adapter import deltas_to_insights

        out = deltas_to_insights(_outputs(health=0.95), "mature")
        assert len(out) == 1
        ins = out[0]
        assert ins.axis == "survival" and ins.feature == "health"
        assert ins.delta == pytest.approx(0.9)
        assert "health" in ins.message.lower()  # increase-direction wording

    def test_negative_direction_uses_decrease_message(self):
        from Programma_CS2_RENAN.backend.coaching.jepa_insight_adapter import deltas_to_insights

        out = deltas_to_insights(_outputs(enemies_visible=0.1), "mature")
        assert out and out[0].axis == "positioning"
        assert "exposure" in out[0].message.lower()

    def test_doubt_hedges_caps_and_halves_confidence(self):
        from Programma_CS2_RENAN.backend.coaching.jepa_insight_adapter import deltas_to_insights

        out = deltas_to_insights(_outputs(health=0.95, enemies_visible=0.1, armor=0.9), "doubt")
        assert len(out) == 1  # cap 1 in doubt
        assert out[0].message.startswith("Observation:")
        assert out[0].confidence == pytest.approx(0.9 * 0.5, abs=1e-3)

    def test_mature_speaks_plainly_top3(self):
        from Programma_CS2_RENAN.backend.coaching.jepa_insight_adapter import deltas_to_insights

        out = deltas_to_insights(
            _outputs(health=0.95, enemies_visible=0.1, armor=0.9, pos_x=0.85),
            "mature",
        )
        assert len(out) == 3  # cap 3, ranked by |delta|
        assert not any(i.message.startswith("Observation:") for i in out)
        mags = [abs(i.delta) for i in out]
        assert mags == sorted(mags, reverse=True)

    def test_semantically_void_direction_is_dropped(self):
        from Programma_CS2_RENAN.backend.coaching.jepa_insight_adapter import deltas_to_insights

        # "be blinded more" has no coaching meaning — increase side is void.
        assert deltas_to_insights(_outputs(is_blinded=0.95), "mature") == []

    def test_unknown_maturity_falls_back_to_doubt(self):
        from Programma_CS2_RENAN.backend.coaching.jepa_insight_adapter import deltas_to_insights

        out = deltas_to_insights(_outputs(health=0.95), "banana")
        assert len(out) == 1 and out[0].message.startswith("Observation:")


class TestLoaderDiscipline:
    def _reset_cache(self):
        from Programma_CS2_RENAN.backend.coaching import jepa_insight_adapter as jia

        jia._MODEL_CACHE.clear()

    def test_missing_checkpoint_yields_none(self, monkeypatch):
        import Programma_CS2_RENAN.backend.nn.persistence as persistence
        from Programma_CS2_RENAN.backend.coaching import jepa_insight_adapter as jia

        self._reset_cache()

        def _missing(version, model, user_id=None):
            raise FileNotFoundError(version)

        monkeypatch.setattr(persistence, "load_nn", _missing)
        assert jia.load_jepa_for_insights() is None
        self._reset_cache()

    def test_stale_checkpoint_yields_none(self, monkeypatch):
        import Programma_CS2_RENAN.backend.nn.persistence as persistence
        from Programma_CS2_RENAN.backend.coaching import jepa_insight_adapter as jia

        self._reset_cache()

        def _stale(version, model, user_id=None):
            raise persistence.StaleCheckpointError("drift")

        monkeypatch.setattr(persistence, "load_nn", _stale)
        assert jia.load_jepa_for_insights() is None
        self._reset_cache()

    def test_setting_off_short_circuits(self, monkeypatch):
        import Programma_CS2_RENAN.core.config as cfg
        from Programma_CS2_RENAN.backend.coaching import jepa_insight_adapter as jia

        monkeypatch.setattr(cfg, "get_setting", lambda key, default=None: False)
        called = mock.MagicMock()
        monkeypatch.setattr(jia, "load_jepa_for_insights", called)
        assert jia.generate_jepa_insights([[0.0] * 25] * 11) == []
        called.assert_not_called()  # flag-off: byte-identical to today (F1.2)

    def test_end_to_end_with_fake_model(self, monkeypatch):
        import torch

        import Programma_CS2_RENAN.core.config as cfg
        from Programma_CS2_RENAN.backend.coaching import jepa_insight_adapter as jia

        def _setting(key, default=None):
            return True if key == "USE_JEPA_MODEL" else default

        monkeypatch.setattr(cfg, "get_setting", _setting)

        fake = mock.MagicMock()
        fake.forward_coaching.return_value = torch.tensor([_outputs(health=0.95)])
        monkeypatch.setattr(jia, "load_jepa_for_insights", lambda: fake)

        out = jia.generate_jepa_insights([[0.0] * 25] * 11, maturity_state="learning")
        assert out and out[0].feature == "health" and out[0].source == "jepa"
        # [T,25] input was auto-batched to [1,T,25]
        (x_arg,), _ = fake.forward_coaching.call_args
        assert tuple(x_arg.shape) == (1, 11, 25)
