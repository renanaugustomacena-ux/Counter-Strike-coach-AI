"""
Shared utilities for the AI Brain Verification Framework.

Provides:
- Cached model instantiation
- Correct-shape random input generation per model type
- Deterministic execution context
- Output stability measurement
- Noise injection
- DB session helper (skip-gate pattern)
"""

import contextlib
import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.config import OUTPUT_DIM, get_device
from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED_A = 42
SEED_B = 123
SEED_C = 7
NOISE_LEVELS = [0.01, 0.05, 0.1, 0.2]

# Verdict types
PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
SKIP = "SKIP"
MANUAL = "MANUAL"
NA = "N/A"

# Model type shortcuts
ALL_MODEL_TYPES = [
    ModelFactory.TYPE_LEGACY,
    ModelFactory.TYPE_JEPA,
    ModelFactory.TYPE_VL_JEPA,
    ModelFactory.TYPE_RAP,
    ModelFactory.TYPE_ROLE_HEAD,
]

# ---------------------------------------------------------------------------
# Cached model instantiation
# ---------------------------------------------------------------------------
_model_cache: Dict[str, nn.Module] = {}


def get_all_models() -> Dict[str, nn.Module]:
    """Cached model instantiation via ModelFactory. Returns dict of type->model."""
    global _model_cache
    if not _model_cache:
        for mt in ALL_MODEL_TYPES:
            try:
                _model_cache[mt] = ModelFactory.get_model(mt)
                _model_cache[mt].eval()
            except Exception as e:
                logging.warning(f"Model '{mt}' unavailable: {e}")
    return _model_cache


def get_model(model_type: str) -> Optional[nn.Module]:
    """Get a single model by type, cached."""
    models = get_all_models()
    return models.get(model_type)


def clear_model_cache():
    """Clear the cached models (useful for training tests)."""
    global _model_cache
    _model_cache.clear()


# ---------------------------------------------------------------------------
# Random input generation
# ---------------------------------------------------------------------------
def get_random_input(
    model_type: str,
    batch_size: int = 2,
    seq_len: int = 10,
    device: Optional[torch.device] = None,
) -> Dict[str, torch.Tensor]:
    """
    Generate correct-shape random tensors for each model type.

    Returns a dict of tensors matching the model's forward() signature.
    """
    if device is None:
        device = torch.device("cpu")

    if model_type == ModelFactory.TYPE_ROLE_HEAD:
        return {"x": torch.randn(batch_size, 5, device=device)}

    if model_type in (
        ModelFactory.TYPE_LEGACY,
        ModelFactory.TYPE_JEPA,
        ModelFactory.TYPE_VL_JEPA,
    ):
        return {"x": torch.randn(batch_size, seq_len, METADATA_DIM, device=device)}

    if model_type == ModelFactory.TYPE_RAP:
        return {
            "view_frame": torch.randn(batch_size, 3, 64, 64, device=device),
            "map_frame": torch.randn(batch_size, 3, 64, 64, device=device),
            "motion_diff": torch.randn(batch_size, 3, 64, 64, device=device),
            "metadata": torch.randn(batch_size, seq_len, METADATA_DIM, device=device),
        }

    raise ValueError(f"Unknown model_type: {model_type}")


def forward_model(model: nn.Module, inputs: Dict[str, torch.Tensor]) -> Any:
    """Run forward pass for any model type with the correct call signature."""
    with torch.no_grad():
        if "view_frame" in inputs:
            # RAP model
            return model(
                inputs["view_frame"],
                inputs["map_frame"],
                inputs["motion_diff"],
                inputs["metadata"],
            )
        else:
            return model(inputs["x"])


# ---------------------------------------------------------------------------
# Deterministic execution context
# ---------------------------------------------------------------------------
@contextlib.contextmanager
def deterministic_context(seed: int = SEED_A):
    """Context manager for deterministic execution (manual_seed + cudnn)."""
    old_cudnn_deterministic = torch.backends.cudnn.deterministic
    old_cudnn_benchmark = torch.backends.cudnn.benchmark
    try:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        np.random.seed(seed)
        yield
    finally:
        torch.backends.cudnn.deterministic = old_cudnn_deterministic
        torch.backends.cudnn.benchmark = old_cudnn_benchmark


def run_deterministic(fn, seed: int = SEED_A):
    """Run function in deterministic context and return result."""
    with deterministic_context(seed):
        return fn()


# ---------------------------------------------------------------------------
# Output stability measurement
# ---------------------------------------------------------------------------
def compute_output_stability(
    model: nn.Module,
    inputs: Dict[str, torch.Tensor],
    n_runs: int = 5,
) -> float:
    """
    Same-input N-run max deviation.
    Returns max absolute deviation across all runs.
    """
    model.eval()
    outputs = []
    for _ in range(n_runs):
        out = forward_model(model, inputs)
        if isinstance(out, dict):
            out = out.get("advice_probs", out.get("coaching_output", next(iter(out.values()))))
        if isinstance(out, torch.Tensor):
            outputs.append(out.detach().cpu().float())

    if len(outputs) < 2:
        return 0.0

    ref = outputs[0]
    max_dev = 0.0
    for o in outputs[1:]:
        dev = torch.max(torch.abs(o - ref)).item()
        max_dev = max(max_dev, dev)
    return max_dev


# ---------------------------------------------------------------------------
# Noise injection
# ---------------------------------------------------------------------------
def add_noise(tensor: torch.Tensor, level: float) -> torch.Tensor:
    """Gaussian noise injection at specified level."""
    noise = torch.randn_like(tensor) * level
    return tensor + noise


# ---------------------------------------------------------------------------
# Tensor output helpers
# ---------------------------------------------------------------------------
def extract_output_tensor(result: Any) -> Optional[torch.Tensor]:
    """Extract the main output tensor from model forward result."""
    if isinstance(result, torch.Tensor):
        return result
    if isinstance(result, dict):
        for key in ["advice_probs", "coaching_output", "concept_probs"]:
            if key in result:
                return result[key]
        # Fallback: first tensor value
        for v in result.values():
            if isinstance(v, torch.Tensor):
                return v
    return None


def has_nan_or_inf(tensor: torch.Tensor) -> bool:
    """Check if tensor contains NaN or Inf values."""
    return bool(torch.isnan(tensor).any() or torch.isinf(tensor).any())


def cosine_similarity(a: torch.Tensor, b: torch.Tensor) -> float:
    """Cosine similarity between two 1D tensors."""
    a_flat = a.flatten().float()
    b_flat = b.flatten().float()
    norm_a = torch.norm(a_flat)
    norm_b = torch.norm(b_flat)
    if norm_a < 1e-8 or norm_b < 1e-8:
        return 0.0
    return float(torch.dot(a_flat, b_flat) / (norm_a * norm_b))


# ---------------------------------------------------------------------------
# DB session helper
# ---------------------------------------------------------------------------
def get_db_session_or_none():
    """Real DB session or None (skip-gate pattern from conftest.py)."""
    try:
        from Programma_CS2_RENAN.backend.storage.database import get_db_manager

        db = get_db_manager()
        session = db.get_session()
        return session
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Rule result dataclass
# ---------------------------------------------------------------------------
class RuleResult:
    """Result of a single rule evaluation."""

    __slots__ = ("rule_id", "name", "verdict", "rule_type", "duration_ms", "evidence", "details")

    def __init__(
        self,
        rule_id: int,
        name: str,
        verdict: str = PASS,
        rule_type: str = "AUTO",
        duration_ms: float = 0.0,
        evidence: Optional[Dict] = None,
        details: str = "",
    ):
        self.rule_id = rule_id
        self.name = name
        self.verdict = verdict
        self.rule_type = rule_type
        self.duration_ms = duration_ms
        self.evidence = evidence or {}
        self.details = details

    def to_dict(self) -> Dict:
        return {
            "id": self.rule_id,
            "name": self.name,
            "verdict": self.verdict,
            "type": self.rule_type,
            "duration_ms": round(self.duration_ms, 1),
            "evidence": self.evidence,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Section result
# ---------------------------------------------------------------------------
class SectionResult:
    """Aggregated results for one section."""

    def __init__(self, section_id: int, name: str):
        self.section_id = section_id
        self.name = name
        self.rules: List[RuleResult] = []

    def add(self, rule: RuleResult):
        self.rules.append(rule)

    @property
    def auto_pass_count(self) -> int:
        return sum(1 for r in self.rules if r.verdict == PASS and r.rule_type == "AUTO")

    @property
    def auto_fail_count(self) -> int:
        return sum(1 for r in self.rules if r.verdict == FAIL and r.rule_type == "AUTO")

    @property
    def auto_total(self) -> int:
        return sum(1 for r in self.rules if r.rule_type == "AUTO")

    def to_dict(self) -> Dict:
        return {
            "id": self.section_id,
            "name": self.name,
            "rules": [r.to_dict() for r in self.rules],
        }


# ---------------------------------------------------------------------------
# Timing helper
# ---------------------------------------------------------------------------
def timed_rule(fn):
    """Decorator to time a rule function and wrap in RuleResult."""

    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if isinstance(result, RuleResult):
            result.duration_ms = elapsed_ms
        return result

    return wrapper
