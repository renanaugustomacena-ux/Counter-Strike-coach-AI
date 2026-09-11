"""D-01: Legacy neural training is frozen by default.

The ALLOW_LEGACY_NEURAL_TRAINING gate (CORREZIONE Parte III §1.1) prevents
construction of TrainingOrchestrator with legacy model types unless the
setting is explicitly True.  The conftest autouse fixture does NOT apply
to this module, so the default (False) is in effect.
"""

from unittest.mock import MagicMock, patch

import pytest
import torch

pytestmark = pytest.mark.timeout(30)


def _make(model_type: str, *, allow_legacy: bool = False):
    """Construct a TrainingOrchestrator under controlled settings."""
    from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

    def _fake_get_setting(key, default=None):
        if key == "ALLOW_LEGACY_NEURAL_TRAINING":
            return allow_legacy
        if key == "USE_RAP_MODEL":
            return True
        return default

    with (
        patch(
            "Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
            return_value=torch.device("cpu"),
        ),
        patch(
            "Programma_CS2_RENAN.core.config.get_setting",
            side_effect=_fake_get_setting,
        ),
    ):
        return TrainingOrchestrator(MagicMock(), model_type=model_type)


class TestLegacyFrozenByDefault:
    """Construction with legacy types raises RuntimeError when gate is False."""

    @pytest.mark.parametrize("model_type", ["jepa", "vl-jepa", "rap"])
    def test_frozen_raises_runtime_error(self, model_type):
        if model_type == "rap":
            pytest.importorskip("ncps")
        with pytest.raises(RuntimeError, match="training is frozen"):
            _make(model_type, allow_legacy=False)

    def test_unknown_type_still_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown model type"):
            _make("nonexistent", allow_legacy=False)

    def test_rap_use_rap_model_precedence(self):
        """USE_RAP_MODEL=False ValueError fires before the freeze gate."""
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        def _no_rap(key, default=None):
            if key == "USE_RAP_MODEL":
                return False
            return default

        with (
            patch(
                "Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                return_value=torch.device("cpu"),
            ),
            patch(
                "Programma_CS2_RENAN.core.config.get_setting",
                side_effect=_no_rap,
            ),
        ):
            with pytest.raises(ValueError, match="USE_RAP_MODEL"):
                TrainingOrchestrator(MagicMock(), model_type="rap")


class TestLegacyAllowedWhenSettingTrue:
    """Construction succeeds when ALLOW_LEGACY_NEURAL_TRAINING=True."""

    def test_jepa_allowed(self):
        orch = _make("jepa", allow_legacy=True)
        assert orch.model_type == "jepa"

    def test_vl_jepa_allowed(self):
        orch = _make("vl-jepa", allow_legacy=True)
        assert orch.model_type == "vl-jepa"

    def test_rap_allowed(self):
        pytest.importorskip("ncps")
        orch = _make("rap", allow_legacy=True)
        assert orch.model_type == "rap"


class TestFreezeConstant:
    """The _LEGACY_TRAIN_TYPES module constant is correct."""

    def test_legacy_types_is_frozenset(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import _LEGACY_TRAIN_TYPES

        assert isinstance(_LEGACY_TRAIN_TYPES, frozenset)
        assert _LEGACY_TRAIN_TYPES == {"jepa", "vl-jepa", "rap", "rap-lite"}
