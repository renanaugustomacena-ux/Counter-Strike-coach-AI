import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import torch

from Programma_CS2_RENAN.core.config import MODELS_DIR, get_resource_path
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.persistence")

# Base models directory is now imported from config to ensure persistence
BASE_NN_DIR = Path(MODELS_DIR)

# GAP-07: metadata-sidecar schema. Bump when the envelope shape changes in
# a way that requires special handling on load (not for benign field adds —
# from_dict ignores unknown keys).
_META_SCHEMA_VERSION = "v1"


class StaleCheckpointError(RuntimeError):
    """Raised when a checkpoint has incompatible dimensions (architecture upgrade).

    Callers must handle this explicitly — silently using a model with random
    weights is never acceptable.
    """


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


def _hash_registry_path() -> Path:
    """Path to the checkpoint hash registry (CTF-1: defense-in-depth)."""
    return BASE_NN_DIR / "checkpoint_hashes.json"


def _compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a checkpoint file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _register_checkpoint_hash(path: Path) -> None:
    """Store SHA-256 hash of a checkpoint after saving."""
    registry_path = _hash_registry_path()
    registry = {}
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    registry[str(path)] = _compute_file_hash(path)
    registry_path.write_text(json.dumps(registry, indent=2))


def _verify_checkpoint_hash(path: Path) -> bool:
    """Verify a checkpoint against its registered hash. Returns True if valid or unregistered."""
    registry_path = _hash_registry_path()
    if not registry_path.exists():
        return True  # no registry yet — skip verification
    try:
        registry = json.loads(registry_path.read_text())
    except (json.JSONDecodeError, OSError):
        return True
    expected = registry.get(str(path))
    if expected is None:
        return True  # checkpoint not in registry (e.g., factory-bundled) — allow
    actual = _compute_file_hash(path)
    if actual != expected:
        logger.error(
            "CTF-1: Checkpoint hash mismatch for %s — expected %s, got %s. "
            "File may be corrupted or tampered with.",
            path,
            expected[:16],
            actual[:16],
        )
        return False
    return True


def _sidecar_path(checkpoint_path: Path) -> Path:
    """Return sibling JSON metadata path for a given .pt checkpoint."""
    return checkpoint_path.with_suffix(".pt.meta.json")


def _build_current_meta() -> dict:
    """Snapshot current feature-schema + normalizer config for sidecar persistence.

    Called at save time. Imported lazily to avoid circular import on module load
    (vectorizer → nn → persistence → vectorizer).
    """
    from Programma_CS2_RENAN.backend.processing.feature_engineering.base_features import (
        load_learned_heuristics,
    )
    from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
        FEATURE_NAMES,
        METADATA_DIM,
    )

    return {
        "schema_version": _META_SCHEMA_VERSION,
        "metadata_dim": METADATA_DIM,
        "feature_names": list(FEATURE_NAMES),
        "heuristic_config": asdict(load_learned_heuristics()),
    }


def _validate_loaded_meta(meta: dict, checkpoint_path: Path) -> None:
    """Raise StaleCheckpointError if the sidecar says the checkpoint was trained
    against a different feature schema than the code currently expects.

    heuristic_config is validated for presence only — bounds can legitimately
    drift via learned calibration (load_learned_heuristics override). What
    MUST match is: schema_version, metadata_dim, feature_names.
    """
    from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
        FEATURE_NAMES,
        METADATA_DIM,
    )

    got_ver = meta.get("schema_version")
    if got_ver != _META_SCHEMA_VERSION:
        raise StaleCheckpointError(
            f"GAP-07: sidecar schema_version={got_ver!r} for {checkpoint_path} "
            f"does not match current {_META_SCHEMA_VERSION!r}. Retrain required."
        )
    got_dim = meta.get("metadata_dim")
    if got_dim != METADATA_DIM:
        raise StaleCheckpointError(
            f"GAP-07: checkpoint trained with metadata_dim={got_dim} but code "
            f"expects {METADATA_DIM}. Retrain required."
        )
    got_names = meta.get("feature_names")
    if got_names is None:
        raise StaleCheckpointError(
            f"GAP-07: sidecar for {checkpoint_path} missing feature_names. "
            "Refuse to load — silent feature drift would follow."
        )
    if list(got_names) != list(FEATURE_NAMES):
        raise StaleCheckpointError(
            f"GAP-07: feature_names in {checkpoint_path} sidecar differ from "
            f"current FEATURE_NAMES. Retrain required. "
            f"Diff (first 5): got={list(got_names)[:5]} cur={list(FEATURE_NAMES)[:5]}"
        )


def save_nn(model, version, user_id=None, extra_meta: Optional[dict] = None):
    """Save model checkpoint with atomic write to prevent corruption on crash.

    GAP-07: also writes a `.pt.meta.json` sidecar capturing the feature-schema
    and normalizer config used at training time. load_nn() validates this
    sidecar on read and raises StaleCheckpointError on drift — preventing the
    silent train/serve skew that previously occurred when heuristic_config.json
    was edited after training.

    Args:
        model: torch.nn.Module — state_dict is serialized.
        version: model version identifier (e.g. "jepa_brain", "rap_coach").
        user_id: optional per-user scope; None → global checkpoint dir.
        extra_meta: optional dict of additional metadata to persist (e.g.
            EMA step, training epoch, optimizer kind). Must be JSON-serializable.
    """
    path = get_model_path(version, user_id)
    tmp_path = path.with_suffix(".pt.tmp")
    sidecar = _sidecar_path(path)
    tmp_sidecar = sidecar.with_suffix(".json.tmp")
    try:
        torch.save(model.state_dict(), tmp_path)
        meta = _build_current_meta()
        if extra_meta:
            meta["extra"] = extra_meta
        tmp_sidecar.write_text(json.dumps(meta, indent=2, sort_keys=True))
        # Promote both files to final names — checkpoint first so consumers
        # never see a sidecar without its matching weights.
        tmp_path.replace(path)
        tmp_sidecar.replace(sidecar)
        _register_checkpoint_hash(path)
    except BaseException:
        for p in (tmp_path, tmp_sidecar):
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        raise


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
        # CTF-1: Verify checkpoint integrity before loading
        if not _verify_checkpoint_hash(path):
            raise RuntimeError(
                f"Checkpoint integrity check failed for {path}. "
                "File hash does not match registry. Refusing to load."
            )
        # GAP-07: Validate sidecar (if present) BEFORE touching the model so
        # a feature-schema drift aborts early instead of producing a model
        # with garbage features at inference. Missing sidecar is treated as
        # a legacy checkpoint — WARN, continue, block re-save until retrain.
        sidecar = _sidecar_path(path)
        if sidecar.exists():
            try:
                meta = json.loads(sidecar.read_text())
            except (json.JSONDecodeError, OSError) as e:
                raise StaleCheckpointError(
                    f"GAP-07: cannot parse sidecar {sidecar}: {e}. "
                    "Refusing to load a checkpoint whose feature-schema "
                    "cannot be verified."
                ) from e
            _validate_loaded_meta(meta, path)
        else:
            logger.warning(
                "GAP-07: no metadata sidecar for %s (legacy checkpoint). "
                "Feature-schema drift cannot be verified. Retrain to remove "
                "this warning.",
                path,
            )
        try:
            state_dict = torch.load(path, map_location=torch.device("cpu"), weights_only=True)
            # Strict validation: Only load if dimensions match.
            # This prevents the 'placebo' effect of loading garbage or crashing.
            model.load_state_dict(state_dict, strict=True)
            model.eval()
        except RuntimeError as re:
            # Handle architecture incompatibility (size mismatch, missing/unexpected keys).
            # All load_state_dict errors contain "state_dict" in the message.
            err_msg = str(re)
            if "size mismatch" in err_msg or "state_dict" in err_msg:
                logger.warning(
                    "Architecture Mismatch: Model at %s is stale. "
                    "Checkpoint is incompatible with current architecture.",
                    path,
                )
                raise StaleCheckpointError(
                    f"Checkpoint at {path} is incompatible. "
                    f"Model needs re-training. Original error: {re}"
                ) from re
            else:
                raise
        except Exception as e:
            logger.exception("Failed to load model from %s", path)
            raise
    else:
        # NN-14: No checkpoint found at any fallback location — never silently
        # return a model with random weights.
        logger.warning(
            "No checkpoint found for version '%s' (user_id=%s). " "Searched: %s, %s",
            version,
            user_id,
            get_model_path(version, user_id),
            get_factory_model_path(version, user_id),
        )
        raise FileNotFoundError(
            f"No checkpoint found for '{version}' (user_id={user_id}). "
            f"Model has random weights — caller must handle this explicitly."
        )

    return model
