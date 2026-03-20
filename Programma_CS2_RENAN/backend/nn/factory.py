"""
Model Factory Module.

Centralizes the instantiation of Neural Networks to ensure consistency
between Training (Teacher) and Inference (Ghost) subsystems.

Supports:
1. Legacy (AdvancedCoachNN) - The default supervised model.
2. JEPA (JEPACoachingModel) - The self-supervised research model.
3. RAP (RAPCoachModel) - The dormant grand vision model.
"""

from typing import Any, Optional

import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.config import HIDDEN_DIM, INPUT_DIM, OUTPUT_DIM
from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM


class ModelFactory:
    """
    Static factory for Neural Network graphs.
    """

    TYPE_LEGACY = "default"
    TYPE_JEPA = "jepa"
    TYPE_VL_JEPA = "vl-jepa"
    TYPE_RAP = "rap"
    TYPE_RAP_LITE = "rap-lite"
    TYPE_ROLE_HEAD = "role_head"

    @staticmethod
    def get_model(model_type: str = "default", **kwargs) -> nn.Module:
        """
        Instantiates a neural network based on type.

        Args:
            model_type: One of "default", "jepa", "rap".
            **kwargs: Additional config passed to constructor.
        """
        if model_type == ModelFactory.TYPE_JEPA:
            from Programma_CS2_RENAN.backend.nn.jepa_model import JEPACoachingModel

            return JEPACoachingModel(
                input_dim=kwargs.get("input_dim", METADATA_DIM),
                output_dim=kwargs.get("output_dim", OUTPUT_DIM),
            )

        elif model_type == ModelFactory.TYPE_VL_JEPA:
            from Programma_CS2_RENAN.backend.nn.jepa_model import VLJEPACoachingModel

            return VLJEPACoachingModel(
                input_dim=kwargs.get("input_dim", METADATA_DIM),
                output_dim=kwargs.get("output_dim", OUTPUT_DIM),
            )

        elif model_type == ModelFactory.TYPE_RAP:
            from Programma_CS2_RENAN.backend.nn.experimental.rap_coach.model import RAPCoachModel

            return RAPCoachModel(
                metadata_dim=kwargs.get("metadata_dim", METADATA_DIM),
                output_dim=kwargs.get("output_dim", 10),
            )

        elif model_type == ModelFactory.TYPE_RAP_LITE:
            from Programma_CS2_RENAN.backend.nn.experimental.rap_coach.model import RAPCoachModel

            return RAPCoachModel(
                metadata_dim=kwargs.get("metadata_dim", METADATA_DIM),
                output_dim=kwargs.get("output_dim", 10),
                use_lite_memory=True,
            )

        elif model_type == ModelFactory.TYPE_ROLE_HEAD:
            from Programma_CS2_RENAN.backend.nn.role_head import NeuralRoleHead

            return NeuralRoleHead(
                input_dim=kwargs.get("input_dim", NeuralRoleHead.ROLE_INPUT_DIM),
                hidden_dim=kwargs.get("hidden_dim", 32),
                output_dim=kwargs.get("output_dim", NeuralRoleHead.ROLE_OUTPUT_DIM),
            )

        elif model_type == ModelFactory.TYPE_LEGACY:
            from Programma_CS2_RENAN.backend.nn.model import TeacherRefinementNN

            return TeacherRefinementNN(
                input_dim=kwargs.get("input_dim", METADATA_DIM),
                output_dim=kwargs.get("output_dim", OUTPUT_DIM),
                hidden_dim=kwargs.get("hidden_dim", HIDDEN_DIM),
            )

        else:
            valid_types = [
                ModelFactory.TYPE_LEGACY,
                ModelFactory.TYPE_JEPA,
                ModelFactory.TYPE_VL_JEPA,
                ModelFactory.TYPE_RAP,
                ModelFactory.TYPE_RAP_LITE,
                ModelFactory.TYPE_ROLE_HEAD,
            ]
            raise ValueError(f"Unknown model type: '{model_type}'. Valid types: {valid_types}")

    @staticmethod
    def get_checkpoint_name(model_type: str) -> str:
        """
        Returns the canonical checkpoint filename for this model type.
        """
        if model_type == ModelFactory.TYPE_JEPA:
            return "jepa_brain"
        elif model_type == ModelFactory.TYPE_VL_JEPA:
            return "vl_jepa_brain"
        elif model_type == ModelFactory.TYPE_RAP:
            return "rap_coach"
        elif model_type == ModelFactory.TYPE_RAP_LITE:
            return "rap_lite_coach"
        elif model_type == ModelFactory.TYPE_ROLE_HEAD:
            return "role_head"
        elif model_type == ModelFactory.TYPE_LEGACY:
            return "latest"
        else:
            valid_types = [
                ModelFactory.TYPE_LEGACY,
                ModelFactory.TYPE_JEPA,
                ModelFactory.TYPE_VL_JEPA,
                ModelFactory.TYPE_RAP,
                ModelFactory.TYPE_RAP_LITE,
                ModelFactory.TYPE_ROLE_HEAD,
            ]
            raise ValueError(
                f"Unknown model type for checkpoint: '{model_type}'. Valid types: {valid_types}"
            )
