import os
from pathlib import Path

import torch

from Programma_CS2_RENAN.core.config import MODELS_DIR, get_resource_path

# Base models directory is now imported from config to ensure persistence
BASE_NN_DIR = Path(MODELS_DIR)


def get_model_path(version, user_id=None):
    if user_id:
        target_dir = BASE_NN_DIR / user_id
    else:
        target_dir = BASE_NN_DIR / "global"

    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{version}.pt"


def get_factory_model_path(version, user_id=None):
    """Returns the path to the read-only model bundled with the executable."""
    rel_path = os.path.join("models", user_id if user_id else "global", f"{version}.pt")
    return Path(get_resource_path(rel_path))


def save_nn(model, version, user_id=None):
    path = get_model_path(version, user_id)
    torch.save(model.state_dict(), path)


def load_nn(version, model, user_id=None):
    # 1. Try local writeable AppData (User learned models)
    path = get_model_path(version, user_id)

    # 2. Try local writeable AppData (Global baseline)
    if not path.exists():
        path = get_model_path(version, None)

    # 3. Try bundled Factory resources (The 'Engine' default)
    if not path.exists():
        path = get_factory_model_path(version, user_id)

    # 4. Final fallback to bundled global
    if not path.exists():
        path = get_factory_model_path(version, None)

    if path.exists():
        try:
            state_dict = torch.load(path, map_location=torch.device("cpu"), weights_only=True)
            # Strict validation: Only load if dimensions match.
            # This prevents the 'placebo' effect of loading garbage or crashing.
            model.load_state_dict(state_dict, strict=True)
            model.eval()
        except RuntimeError as re:
            # Handle size mismatch (common during architecture upgrades)
            if "size mismatch" in str(re):
                from Programma_CS2_RENAN.core.logger import app_logger

                app_logger.warning(
                    "Architecture Mismatch: Model at %s is stale (old dims). Running with fresh initialization.",
                    path,
                )
                # Flag the model as untrained so callers can check (F3-23)
                model._stale_checkpoint = True
                app_logger.warning(
                    "PREDICTION QUALITY: Model is running with RANDOM WEIGHTS after stale "
                    "checkpoint detection. All predictions are meaningless until re-training completes."
                )
            else:
                raise
        except Exception as e:
            from Programma_CS2_RENAN.core.logger import app_logger

            app_logger.error("Failed to load model from %s: %s", path, e)

    return model
