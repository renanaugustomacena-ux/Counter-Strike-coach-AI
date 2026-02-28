"""
Section 13: Deployment Readiness (Rules 99-107)

Tests reliability, load testing, disaster recovery, continuous learning,
backward compatibility, technical debt, documentation, and user help.
Auto: 6, Manual: 3
"""

import json
import logging
import os
import tempfile
import time

import torch

from Programma_CS2_RENAN.backend.nn.config import OUTPUT_DIM
from Programma_CS2_RENAN.tools.brain_verification._common import (
    ALL_MODEL_TYPES,
    FAIL,
    MANUAL,
    METADATA_DIM,
    PASS,
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
    has_nan_or_inf,
)


def run(quick: bool = False) -> SectionResult:
    section = SectionResult(13, "Deployment Readiness")

    section.add(_rule_99())
    section.add(_rule_100())
    section.add(_rule_101())
    section.add(_rule_102())
    section.add(_rule_103())
    section.add(_rule_104())
    section.add(_rule_105())
    section.add(_rule_106())
    section.add(_rule_107())

    return section


def _rule_99() -> RuleResult:
    """Reliability: 100 forward passes per model. Zero failures."""
    t0 = time.perf_counter()
    models = get_all_models()
    results = {}
    total_failures = 0

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA, ModelFactory.TYPE_ROLE_HEAD]:
        model = models.get(mt)
        if model is None:
            continue
        model.eval()

        failures = 0
        for i in range(100):
            try:
                inputs = get_random_input(mt, batch_size=1, seq_len=10)
                with torch.no_grad():
                    out = forward_model(model, inputs)
                t = extract_output_tensor(out)
                if t is None or has_nan_or_inf(t):
                    failures += 1
            except Exception as e:
                logging.warning(
                    f"Rule 99 forward pass failed for {mt} iter {i}: {type(e).__name__}: {e}"
                )
                failures += 1

        results[mt] = {"passes": 100 - failures, "failures": failures}
        total_failures += failures

    passed = total_failures == 0
    return RuleResult(
        99,
        "Reliability",
        PASS if passed else FAIL,
        evidence=results,
        details=f"100 passes per model: {total_failures} total failures",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_100() -> RuleResult:
    """Load testing: batch=64 forward pass, all models. <5s on CPU."""
    t0 = time.perf_counter()
    models = get_all_models()
    results = {}
    all_ok = True

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA, ModelFactory.TYPE_ROLE_HEAD]:
        model = models.get(mt)
        if model is None:
            continue
        model.eval()

        inputs = get_random_input(mt, batch_size=64, seq_len=10)
        ts = time.perf_counter()
        try:
            with torch.no_grad():
                out = forward_model(model, inputs)
            elapsed = (time.perf_counter() - ts) * 1000
            t = extract_output_tensor(out)
            valid = t is not None and not has_nan_or_inf(t)
            ok = elapsed < 5000 and valid
        except Exception as e:
            elapsed = (time.perf_counter() - ts) * 1000
            ok = False

        if not ok:
            all_ok = False
        results[mt] = {"elapsed_ms": round(elapsed, 1), "ok": ok, "limit_ms": 5000}

    return RuleResult(
        100,
        "Load testing",
        PASS if all_ok else WARN,
        evidence=results,
        details="Batch=64: " + ", ".join(f"{k}={v['elapsed_ms']}ms" for k, v in results.items()),
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_101() -> RuleResult:
    """Disaster recovery: save checkpoint + metadata -> load -> functional model."""
    t0 = time.perf_counter()

    with tempfile.TemporaryDirectory() as tmpdir:
        ckpt_path = os.path.join(tmpdir, "dr_checkpoint.pt")
        meta_path = os.path.join(tmpdir, "dr_meta.json")

        # Create and save
        model = ModelFactory.get_model(ModelFactory.TYPE_LEGACY)
        torch.save(model.state_dict(), ckpt_path)
        meta = {"model_type": "legacy", "version": "1.0", "timestamp": "2026-02-17"}
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        # Load and verify functional
        model2 = ModelFactory.get_model(ModelFactory.TYPE_LEGACY)
        model2.load_state_dict(torch.load(ckpt_path, weights_only=True))
        model2.eval()

        x = torch.randn(2, 10, METADATA_DIM)
        with torch.no_grad():
            out = model2(x)
        functional = out is not None and not has_nan_or_inf(out)

        # Verify metadata
        with open(meta_path) as f:
            loaded = json.load(f)
        meta_ok = loaded.get("model_type") == "legacy"

    passed = functional and meta_ok
    return RuleResult(
        101,
        "Disaster recovery",
        PASS if passed else FAIL,
        evidence={"functional": functional, "metadata_roundtrip": meta_ok},
        details=f"DR roundtrip: functional={functional}, metadata={meta_ok}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_102() -> RuleResult:
    """Continuous learning: TrainingOrchestrator instantiates for jepa and rap."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator
    except ImportError:
        return RuleResult(
            102, "Continuous learning", SKIP, details="TrainingOrchestrator not available"
        )

    from Programma_CS2_RENAN.tools.brain_verification._common import get_db_session_or_none

    manager = get_db_session_or_none()

    results = {}
    for mt in ["jepa", "rap"]:
        try:
            orch = TrainingOrchestrator(manager=manager, model_type=mt, max_epochs=1)
            # Verify key attributes are initialized
            results[mt] = hasattr(orch, "model_type") and orch.model_type == mt
        except Exception as e:
            results[mt] = str(e)[:60]

    passed = all(v is True for v in results.values())
    return RuleResult(
        102,
        "Continuous learning",
        PASS if passed else (WARN if manager is None else FAIL),
        evidence={**results, "manager_available": manager is not None},
        details=f"TrainingOrchestrator: jepa={results.get('jepa')}, rap={results.get('rap')}, db={'real' if manager else 'None'}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_103() -> RuleResult:
    """Backward compatibility: ModelFactory supports all 5 type constants."""
    t0 = time.perf_counter()
    results = {}
    all_ok = True

    expected = {
        ModelFactory.TYPE_LEGACY: "AdvancedCoachNN",
        ModelFactory.TYPE_JEPA: "JEPACoachingModel",
        ModelFactory.TYPE_VL_JEPA: "VLJEPACoachingModel",
        ModelFactory.TYPE_RAP: "RAPCoachModel",
        ModelFactory.TYPE_ROLE_HEAD: "NeuralRoleHead",
    }

    for mt, expected_class in expected.items():
        try:
            model = ModelFactory.get_model(mt)
            class_name = model.__class__.__name__
            correct = expected_class in class_name or class_name == expected_class
            results[mt] = {"class": class_name, "expected": expected_class, "ok": correct}
            if not correct:
                all_ok = False
        except Exception as e:
            results[mt] = {"error": str(e)[:60]}
            all_ok = False

    return RuleResult(
        103,
        "Backward compatibility",
        PASS if all_ok else FAIL,
        evidence=results,
        details=f"ModelFactory: {sum(1 for r in results.values() if isinstance(r, dict) and r.get('ok'))}/5 correct",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_104() -> RuleResult:
    """Technical debt (MANUAL): run Goliath Oncology department."""
    return RuleResult(
        104,
        "Technical debt",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: run Goliath_Hospital.py and review Oncology "
        "department findings. Document technical debt items.",
    )


def _rule_105() -> RuleResult:
    """Documentation (MANUAL): verify public APIs have docstrings."""
    return RuleResult(
        105,
        "Documentation",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: verify public APIs have docstrings. "
        "Run pydocstyle or similar tool.",
    )


def _rule_106() -> RuleResult:
    """Knowledge transfer (MANUAL): verify MEMORY.md + CLAUDE.md contain architecture docs."""
    return RuleResult(
        106,
        "Knowledge transfer",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: verify MEMORY.md and CLAUDE.md contain "
        "comprehensive architecture documentation.",
    )


def _rule_107() -> RuleResult:
    """User documentation: help_screen.py exists and contains content."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.apps.desktop_app.help_screen import HelpScreen

        exists = True
    except ImportError:
        exists = False

    if exists:
        # Check it has content methods
        has_load = hasattr(HelpScreen, "load_topics") or hasattr(HelpScreen, "load_content")
    else:
        has_load = False

    passed = exists and has_load
    return RuleResult(
        107,
        "User documentation",
        PASS if passed else FAIL,
        evidence={"help_screen_exists": exists, "has_content_methods": has_load},
        details=f"help_screen.py: exists={exists}, has_content={has_load}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )
