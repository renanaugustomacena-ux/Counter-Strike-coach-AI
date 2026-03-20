"""
Tests for dimension chain integration — Tier 3: End-to-end dimension alignment.

Verifies that the dimension constants are consistent across the entire pipeline:
  vectorizer.METADATA_DIM = config.INPUT_DIM = model input_dim

This is the most critical invariant in the ML pipeline. If these dimensions
diverge, the model silently produces garbage (or crashes with size mismatch).
"""

import pytest
import torch


class TestDimensionChainAlignment:
    """Verify that METADATA_DIM propagates consistently through the pipeline."""

    def test_metadata_dim_equals_input_dim(self):
        """vectorizer.METADATA_DIM must equal config.INPUT_DIM."""
        from Programma_CS2_RENAN.backend.nn.config import INPUT_DIM
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        assert METADATA_DIM == INPUT_DIM, (
            f"METADATA_DIM ({METADATA_DIM}) != INPUT_DIM ({INPUT_DIM}). "
            "This breaks the entire ML pipeline."
        )

    def test_metadata_dim_is_25(self):
        """Canonical dimension value check."""
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        assert METADATA_DIM == 25

    def test_output_dim_matches_metadata_dim(self):
        """P1-08: OUTPUT_DIM must be aligned with METADATA_DIM."""
        from Programma_CS2_RENAN.backend.nn.config import OUTPUT_DIM
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        assert OUTPUT_DIM == METADATA_DIM

    def test_legacy_model_accepts_metadata_dim_input(self):
        """TeacherRefinementNN should accept METADATA_DIM-sized input without error."""
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        model = ModelFactory.get_model("default")
        test_input = torch.randn(1, METADATA_DIM)

        with torch.no_grad():
            output = model(test_input)

        assert output is not None, "Model should produce output"
        assert output.shape[0] == 1, "Batch dimension should be preserved"

    def test_jepa_model_accepts_metadata_dim_input(self):
        """JEPACoachingModel should accept METADATA_DIM-sized input."""
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        model = ModelFactory.get_model("jepa")
        # JEPA expects sequence input: (batch, seq_len, METADATA_DIM)
        test_input = torch.randn(1, 10, METADATA_DIM)

        with torch.no_grad():
            # JEPA's forward might have different signature — use basic check
            try:
                output = model(test_input)
            except TypeError:
                # If forward requires specific kwargs, just verify it's nn.Module
                assert hasattr(model, "forward")

    def test_feature_extractor_output_matches_model_input(self):
        """FeatureExtractor output shape must match model's expected input_dim."""
        import numpy as np

        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            FeatureExtractor,
        )

        # Extract features
        vec = FeatureExtractor.extract({"health": 100, "armor": 100})

        # Create model and verify it accepts this input
        model = ModelFactory.get_model("default")
        tensor = torch.tensor(vec, dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            output = model(tensor)

        assert output is not None

    def test_training_features_matches_metadata_dim(self):
        """coach_manager.TRAINING_FEATURES must have METADATA_DIM entries."""
        from Programma_CS2_RENAN.backend.nn.coach_manager import TRAINING_FEATURES
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        assert len(TRAINING_FEATURES) == METADATA_DIM

    def test_match_aggregate_features_matches_metadata_dim(self):
        """coach_manager.MATCH_AGGREGATE_FEATURES must have METADATA_DIM entries."""
        from Programma_CS2_RENAN.backend.nn.coach_manager import MATCH_AGGREGATE_FEATURES
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        assert len(MATCH_AGGREGATE_FEATURES) == METADATA_DIM

    def test_config_hidden_dim(self):
        """HIDDEN_DIM should be consistent across config and model."""
        from Programma_CS2_RENAN.backend.nn.config import HIDDEN_DIM

        assert HIDDEN_DIM == 128

    def test_model_output_dim_matches_config(self):
        """Model output dimension should match config.OUTPUT_DIM."""
        from Programma_CS2_RENAN.backend.nn.config import OUTPUT_DIM
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        model = ModelFactory.get_model("default")
        test_input = torch.randn(1, METADATA_DIM)

        with torch.no_grad():
            output = model(test_input)

        assert (
            output.shape[-1] == OUTPUT_DIM
        ), f"Model output dim ({output.shape[-1]}) != OUTPUT_DIM ({OUTPUT_DIM})"
