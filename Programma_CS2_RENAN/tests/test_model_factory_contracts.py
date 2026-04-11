"""
Tests for factory.py — Bug #2: Unknown model_type silently returns legacy model.

ModelFactory.get_model() uses an if/elif/else chain where the `else` branch
returns TeacherRefinementNN for ANY unrecognized model_type string. This means
typos like "jep" or completely invalid types like "transformer" silently produce
a legacy model instead of raising an error.

These tests verify:
1. Each valid model type returns the correct class
2. Invalid model types raise ValueError (desired behavior — currently FAILS)
3. Dimension parameters are correctly propagated
4. Checkpoint name resolution works for all types
"""

import pytest
import torch.nn as nn


class TestValidModelTypes:
    """Verify that each valid model type produces the correct class."""

    def test_legacy_default_type(self):
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        model = ModelFactory.get_model("default")
        from Programma_CS2_RENAN.backend.nn.model import TeacherRefinementNN

        assert isinstance(
            model, TeacherRefinementNN
        ), f"'default' type should return TeacherRefinementNN, got {type(model).__name__}"

    def test_jepa_type(self):
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        model = ModelFactory.get_model("jepa")
        from Programma_CS2_RENAN.backend.nn.jepa_model import JEPACoachingModel

        assert isinstance(
            model, JEPACoachingModel
        ), f"'jepa' type should return JEPACoachingModel, got {type(model).__name__}"

    def test_vl_jepa_type(self):
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        model = ModelFactory.get_model("vl-jepa")
        from Programma_CS2_RENAN.backend.nn.jepa_model import VLJEPACoachingModel

        assert isinstance(
            model, VLJEPACoachingModel
        ), f"'vl-jepa' type should return VLJEPACoachingModel, got {type(model).__name__}"

    def test_rap_type(self):
        pytest.importorskip("ncps", reason="ncps not installed")
        pytest.importorskip("hflayers", reason="hflayers not installed")
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        model = ModelFactory.get_model("rap")
        from Programma_CS2_RENAN.backend.nn.rap_coach.model import RAPCoachModel

        assert isinstance(
            model, RAPCoachModel
        ), f"'rap' type should return RAPCoachModel, got {type(model).__name__}"

    def test_role_head_type(self):
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        model = ModelFactory.get_model("role_head")
        from Programma_CS2_RENAN.backend.nn.role_head import NeuralRoleHead

        assert isinstance(
            model, NeuralRoleHead
        ), f"'role_head' type should return NeuralRoleHead, got {type(model).__name__}"

    def test_all_valid_types_are_nn_modules(self):
        """Every valid type must return an nn.Module instance (types with available deps only)."""
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        # Only test types whose dependencies are available
        types_to_test = ["default", "jepa", "vl-jepa"]
        try:
            import hflayers  # noqa: F401
            import ncps  # noqa: F401

            types_to_test.append("rap")
        except ImportError:
            pass

        for model_type in types_to_test:
            model = ModelFactory.get_model(model_type)
            assert isinstance(
                model, nn.Module
            ), f"Type '{model_type}' returned {type(model)}, not nn.Module"


class TestInvalidModelTypes:
    """BUG #2: These tests EXPOSE the silent fallback for unknown types.

    These tests are expected to FAIL until the bug is fixed.
    """

    def test_unknown_type_should_raise_error(self):
        """An unrecognized model_type must raise ValueError, not silently return default.

        CURRENTLY FAILS: factory.py line 74 returns TeacherRefinementNN for any
        unrecognized type via the `else` branch.
        """
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        with pytest.raises(ValueError, match="Unknown model type"):
            ModelFactory.get_model("totally_invalid_type")

    def test_typo_jepa_should_raise_error(self):
        """A typo like 'jep' should raise, not silently produce a legacy model.

        CURRENTLY FAILS: 'jep' falls through to else branch.
        """
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        with pytest.raises(ValueError):
            ModelFactory.get_model("jep")

    def test_empty_string_should_raise_error(self):
        """Empty string is not a valid model type.

        CURRENTLY FAILS: empty string falls through to else branch.
        """
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        with pytest.raises(ValueError):
            ModelFactory.get_model("")

    def test_none_type_should_raise_error(self):
        """None is not a valid model type."""
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        with pytest.raises((ValueError, TypeError)):
            ModelFactory.get_model(None)

    def test_case_sensitivity(self):
        """Model types should be case-sensitive — 'JEPA' is not 'jepa'.

        CURRENTLY FAILS: 'JEPA' falls through to else branch and returns legacy.
        """
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        with pytest.raises(ValueError):
            ModelFactory.get_model("JEPA")


class TestDimensionPropagation:
    """Verify that dimension kwargs are correctly forwarded to model constructors."""

    def test_legacy_custom_dimensions(self):
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        model = ModelFactory.get_model("default", input_dim=10, output_dim=3, hidden_dim=32)
        # Verify by checking the LSTM input size
        assert (
            model.lstm.input_size == 10
        ), f"input_dim not propagated: expected 10, got {model.lstm.input_size}"

    def test_legacy_default_dimensions(self):
        """Default dimensions should match METADATA_DIM and OUTPUT_DIM from config."""
        from Programma_CS2_RENAN.backend.nn.config import INPUT_DIM, OUTPUT_DIM
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        model = ModelFactory.get_model("default")
        assert (
            model.lstm.input_size == METADATA_DIM
        ), f"Default input_dim should be METADATA_DIM={METADATA_DIM}, got {model.lstm.input_size}"

    def test_jepa_custom_dimensions(self):
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        model = ModelFactory.get_model("jepa", input_dim=15, output_dim=6)
        # JEPACoachingModel should accept these dimensions
        assert isinstance(model, nn.Module)


class TestCheckpointNameResolution:
    """Verify checkpoint name mapping for each model type."""

    def test_checkpoint_names(self):
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        expected = {
            "default": "latest",
            "jepa": "jepa_brain",
            "vl-jepa": "vl_jepa_brain",
            "rap": "rap_coach",
            "role_head": "role_head",
        }
        for model_type, expected_name in expected.items():
            actual = ModelFactory.get_checkpoint_name(model_type)
            assert (
                actual == expected_name
            ), f"Checkpoint for '{model_type}': expected '{expected_name}', got '{actual}'"

    def test_unknown_checkpoint_name_raises_error(self):
        """Unknown type should raise ValueError for checkpoint name too."""
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        with pytest.raises(ValueError, match="Unknown model type"):
            ModelFactory.get_checkpoint_name("invalid")


class TestTypeConstants:
    """Verify type constants are consistent and complete."""

    def test_all_constants_defined(self):
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        assert ModelFactory.TYPE_LEGACY == "default"
        assert ModelFactory.TYPE_JEPA == "jepa"
        assert ModelFactory.TYPE_VL_JEPA == "vl-jepa"
        assert ModelFactory.TYPE_RAP == "rap"
        assert ModelFactory.TYPE_ROLE_HEAD == "role_head"

    def test_all_constants_produce_valid_models(self):
        """Every TYPE_* constant must be a valid input to get_model (with available deps)."""
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        # Skip types that require optional dependencies (ncps + hflayers)
        skip_types = set()
        try:
            import hflayers  # noqa: F401
            import ncps  # noqa: F401
        except ImportError:
            skip_types.add("rap")
            skip_types.add("rap-lite")

        for attr_name in dir(ModelFactory):
            if attr_name.startswith("TYPE_"):
                model_type = getattr(ModelFactory, attr_name)
                if model_type in skip_types:
                    continue
                model = ModelFactory.get_model(model_type)
                assert isinstance(
                    model, nn.Module
                ), f"TYPE constant '{attr_name}' = '{model_type}' failed to produce a valid model"
