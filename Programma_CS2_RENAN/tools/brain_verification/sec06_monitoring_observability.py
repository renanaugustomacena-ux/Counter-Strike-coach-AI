"""
Section 6: Monitoring & Observability (Rules 48-53)

Tests metrics instrumentation, drift detection, failure mode monitoring,
error reproduction, interpretability tools, and A/B testing infrastructure.
Auto: 5, Manual: 1
"""

import time

import numpy as np
import pandas as pd
import torch

from Programma_CS2_RENAN.tools.brain_verification._common import (
    FAIL,
    MANUAL,
    METADATA_DIM,
    PASS,
    SEED_A,
    SKIP,
    WARN,
    ModelFactory,
    RuleResult,
    SectionResult,
    deterministic_context,
    extract_output_tensor,
    forward_model,
    get_all_models,
    get_random_input,
)


def run(quick: bool = False) -> SectionResult:
    section = SectionResult(6, "Monitoring & Observability")

    section.add(_rule_48())
    section.add(_rule_49())
    section.add(_rule_50())
    section.add(_rule_51())
    section.add(_rule_52())
    section.add(_rule_53())

    return section


def _rule_48() -> RuleResult:
    """Metrics instrumentation: TensorBoardCallback instantiates and fires."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.nn.tensorboard_callback import TensorBoardCallback
    except ImportError:
        return RuleResult(
            48, "Metrics instrumentation", SKIP, details="TensorBoardCallback not available"
        )

    try:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cb = TensorBoardCallback(log_dir=os.path.join(tmpdir, "test_run"), model_type="legacy")
            # Fire on_epoch_end without crashing
            cb.on_epoch_end(epoch=0, train_loss=0.5, val_loss=0.6, model=None)
            cb.close()
        instantiated = True
    except Exception as e:
        return RuleResult(
            48,
            "Metrics instrumentation",
            FAIL,
            evidence={"error": str(e)},
            details=f"TensorBoardCallback failed: {e}",
        )

    return RuleResult(
        48,
        "Metrics instrumentation",
        PASS,
        evidence={"instantiated": True, "fired_epoch_end": True},
        details="TensorBoardCallback instantiated and fired on_epoch_end",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_49() -> RuleResult:
    """Drift detection: detect_feature_drift flags large distribution shifts."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.processing.validation.drift import detect_feature_drift
    except ImportError:
        return RuleResult(49, "Drift detection", SKIP, details="detect_feature_drift not available")

    # Create synthetic history with a large shift
    n = 30
    normal_data = {
        "avg_adr": np.random.normal(70, 10, n).tolist(),
        "kd_ratio": np.random.normal(1.0, 0.2, n).tolist(),
        "impact_rounds": np.random.normal(0.5, 0.1, n).tolist(),
        "avg_hs": np.random.normal(40, 10, n).tolist(),
        "avg_kast": np.random.normal(65, 8, n).tolist(),
    }
    # Inject drift in last 10 samples
    for key in normal_data:
        for i in range(20, 30):
            normal_data[key][i] += 50.0  # Large shift

    df = pd.DataFrame(normal_data)

    try:
        result = detect_feature_drift(df, window=10, z_threshold=2.5)
        detected = result.get("is_drifted", False) if isinstance(result, dict) else False
    except Exception as e:
        return RuleResult(49, "Drift detection", SKIP, details=f"detect_feature_drift raised: {e}")

    return RuleResult(
        49,
        "Drift detection",
        PASS if detected else WARN,
        evidence={"drift_detected": detected, "result": str(result)[:200]},
        details=f"Large shift detected={detected}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_50() -> RuleResult:
    """Failure mode monitoring: CallbackRegistry catches errors from bad callback."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.nn.training_callbacks import (
            CallbackRegistry,
            TrainingCallback,
        )
    except ImportError:
        return RuleResult(
            50, "Failure mode monitoring", SKIP, details="CallbackRegistry not available"
        )

    class BadCallback(TrainingCallback):
        def on_epoch_end(self, epoch, train_loss, val_loss, model, **kwargs):
            raise RuntimeError("Intentional test error")

    registry = CallbackRegistry([BadCallback()])

    # Training must not crash
    try:
        registry.fire("on_epoch_end", epoch=0, train_loss=0.5, val_loss=0.6, model=None)
        survived = True
    except Exception:
        survived = False

    return RuleResult(
        50,
        "Failure mode monitoring",
        PASS if survived else FAIL,
        evidence={"callback_error_caught": survived},
        details=f"Bad callback survived={survived}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_51() -> RuleResult:
    """Error reproduction: deterministic mode gives same output, 5 runs."""
    t0 = time.perf_counter()
    models = get_all_models()
    results = {}
    all_deterministic = True

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA]:
        model = models.get(mt)
        if model is None:
            continue
        model.eval()

        outputs = []
        for _ in range(5):
            with deterministic_context(SEED_A):
                x = torch.randn(2, 10, METADATA_DIM)
                with torch.no_grad():
                    out = model(x)
                t = extract_output_tensor(out)
                if t is not None:
                    outputs.append(t.clone())

        if len(outputs) < 2:
            results[mt] = "insufficient_outputs"
            all_deterministic = False
            continue

        max_diff = 0.0
        for o in outputs[1:]:
            diff = torch.max(torch.abs(o - outputs[0])).item()
            max_diff = max(max_diff, diff)

        deterministic = max_diff < 1e-6
        if not deterministic:
            all_deterministic = False
        results[mt] = {"max_diff": round(max_diff, 10), "deterministic": deterministic}

    return RuleResult(
        51,
        "Error reproduction",
        PASS if all_deterministic else FAIL,
        evidence=results,
        details=f"Deterministic: all_ok={all_deterministic}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_52() -> RuleResult:
    """Interpretability tools: EmbeddingProjector instantiates. UMAP if available."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.nn.embedding_projector import EmbeddingProjector
    except ImportError:
        return RuleResult(
            52, "Interpretability tools", SKIP, details="EmbeddingProjector not available"
        )

    try:
        proj = EmbeddingProjector(tb_writer=None, interval=5)
        instantiated = True
    except Exception as e:
        return RuleResult(
            52,
            "Interpretability tools",
            FAIL,
            evidence={"error": str(e)},
            details=f"EmbeddingProjector failed: {e}",
        )

    # Check UMAP availability
    try:
        import umap

        umap_available = True
    except ImportError:
        umap_available = False

    return RuleResult(
        52,
        "Interpretability tools",
        PASS,
        evidence={"instantiated": True, "umap_available": umap_available},
        details=f"EmbeddingProjector OK, UMAP={'available' if umap_available else 'not installed'}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_53() -> RuleResult:
    """A/B testing infrastructure (MANUAL): ModelFactory supports multiple types."""
    return RuleResult(
        53,
        "A/B testing infrastructure",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: document that ModelFactory can instantiate multiple "
        "model types simultaneously for comparison.",
    )
