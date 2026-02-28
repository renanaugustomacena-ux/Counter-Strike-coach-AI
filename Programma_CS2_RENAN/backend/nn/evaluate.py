import numpy as np
import torch

try:
    import shap

    _HAS_SHAP = True
except ImportError:
    _HAS_SHAP = False

from Programma_CS2_RENAN.backend.nn.config import WEIGHT_CLAMP
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.evaluate")


def evaluate_adjustments(model, X_sample, role_id=None):
    """
    Evaluates adjustments AND provides SHAP explanations (Item 1).
    """
    model.eval()

    # Prep tensor
    X_tensor = torch.tensor(X_sample, dtype=torch.float32)
    if X_tensor.ndim == 1:
        X_tensor = X_tensor.unsqueeze(0)

    # 1. Prediction with Role Context
    with torch.no_grad():
        adj = model(X_tensor, role_id=role_id).squeeze(0)

    # 2. Explanation (SHAP)
    shap_values = None
    if _HAS_SHAP:
        def model_wrapper(x):
            t = torch.tensor(x, dtype=torch.float32)
            with torch.no_grad():
                return model(t).numpy()

        # WARNING (F3-18): Zero-vector baseline biases SHAP attributions toward features with
        # non-zero values — features like position (pos_x, pos_y) will appear more important
        # than they actually are. Replace np.zeros with the mean of a representative training
        # sample for calibrated explanations.
        explainer = shap.KernelExplainer(model_wrapper, np.zeros((1, X_tensor.shape[1])))
        shap_values = explainer.shap_values(X_tensor.numpy())
    else:
        logger.warning("shap not installed — SHAP explanations unavailable. Install with: pip install shap")

    return {
        "adr_weight": float(adj[0]) * WEIGHT_CLAMP,
        "kast_weight": float(adj[1]) * WEIGHT_CLAMP,
        "hs_weight": float(adj[2]) * WEIGHT_CLAMP,
        "impact_weight": float(adj[3]) * WEIGHT_CLAMP,
        "explanations": shap_values,
    }
