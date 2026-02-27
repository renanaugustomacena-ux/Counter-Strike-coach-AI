import os

import torch

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.brain_bridge")

try:
    from .feature_engineering import BrainFeatureEngineer
    from .superposition_net import AdaptiveSuperpositionMLP
except ImportError:
    # Standalone execution fallback
    from feature_engineering import BrainFeatureEngineer
    from superposition_net import AdaptiveSuperpositionMLP

# Locate model weights relative to this file
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "nn", "brain_v1.pt"
)


class BrainBridge:
    """
    The production bridge for the Advanced Brain Model.
    Provides CSI analysis and Superposition-based adjustments.
    """

    def __init__(self):
        self.fe = BrainFeatureEngineer()
        self.model = AdaptiveSuperpositionMLP(input_dim=12)  # BrainFeatureEngineer pipeline
        self._load_model_weights()

    def _load_model_weights(self):
        if not os.path.exists(MODEL_PATH):
            return
        try:
            self.model.load_state_dict(
                torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
            )
            self.model.eval()
        except Exception as e:
            logger.warning("Failed to load model weights from %s: %s", MODEL_PATH, e)
            self.model = None

    def get_advanced_metrics(self, stats_dict):
        """
        Calculates CSI and Stability without needing the full NN if not loaded.
        """
        brain_feats = self.fe.process_match_snapshot(stats_dict)
        return {"csi": brain_feats["csi"], "urgency": brain_feats["tactical_urgency"]}

    def generate_brain_insights(self, features_list, context_list):
        """
        Full inference using Superposition.
        """
        if self.model is None:
            logger.warning("BrainBridge model not loaded — skipping inference")
            return {"impact": 0.0, "adjustments": []}

        feats_tensor = torch.tensor([features_list], dtype=torch.float32)
        context_tensor = torch.tensor([context_list], dtype=torch.float32)

        with torch.no_grad():
            outputs = self.model(feats_tensor, context_tensor)

        return {
            "impact": float(outputs["impact"]),
            "adjustments": outputs["feedback"].squeeze().tolist(),
        }
