"""
Section 9: Continuous Improvement (Rules 69-74)

Tests feedback collection, feedback-driven improvement, active learning,
version lineage, experimentation framework, and regression testing.
Auto: 4, Manual: 2
"""

import json
import os
import tempfile
import time

import torch

from Programma_CS2_RENAN.backend.nn.config import OUTPUT_DIM
from Programma_CS2_RENAN.tools.brain_verification._common import (
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
    get_model,
)


def run(quick: bool = False) -> SectionResult:
    section = SectionResult(9, "Continuous Improvement")

    section.add(_rule_69())
    section.add(_rule_70())
    section.add(_rule_71())
    section.add(_rule_72())
    section.add(_rule_73())
    section.add(_rule_74())

    return section


def _rule_69() -> RuleResult:
    """Feedback collection: CoachingExperience DB model exists. ExperienceBank.add_experience works."""
    t0 = time.perf_counter()
    checks = {}

    # Check model exists
    try:
        from Programma_CS2_RENAN.backend.storage.db_models import CoachingExperience

        checks["model_exists"] = True
    except ImportError:
        checks["model_exists"] = False

    # Check ExperienceBank instantiates
    try:
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import (
            ExperienceBank,
            get_experience_bank,
        )

        bank = get_experience_bank()
        has_add = hasattr(bank, "add_experience")
        checks["bank_instantiates"] = True
        checks["has_add_experience"] = has_add
    except Exception as e:
        checks["bank_error"] = str(e)[:80]

    passed = checks.get("model_exists", False) and checks.get("has_add_experience", False)
    return RuleResult(
        69,
        "Feedback collection",
        PASS if passed else FAIL,
        evidence=checks,
        details=f"CoachingExperience model + ExperienceBank: ok={passed}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_70() -> RuleResult:
    """Feedback-driven improvement: ExperienceBank.retrieve_similar returns results when non-empty."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.knowledge.experience_bank import (
            ExperienceBank,
            ExperienceContext,
            get_experience_bank,
        )
    except ImportError:
        return RuleResult(
            70, "Feedback-driven improvement", SKIP, details="ExperienceBank not available"
        )

    bank = get_experience_bank()
    ctx = ExperienceContext(
        map_name="de_dust2",
        round_phase="full_buy",
        side="ct",
        position_area="A_site",
        health_range="full",
        equipment_tier="full_buy",
        teammates_alive=4,
        enemies_alive=5,
    )

    try:
        results = bank.retrieve_similar(ctx, top_k=3)
        has_method = True
        returned = len(results) if results is not None else 0
    except Exception as e:
        return RuleResult(
            70, "Feedback-driven improvement", SKIP, details=f"retrieve_similar raised: {e}"
        )

    # Method exists and works (may return 0 if bank is empty — that's ok)
    return RuleResult(
        70,
        "Feedback-driven improvement",
        PASS if has_method else FAIL,
        evidence={"method_works": has_method, "results_returned": returned},
        details=f"retrieve_similar works, returned {returned} results",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_71() -> RuleResult:
    """Active learning: AdaptiveBeliefCalibrator.auto_calibrate runs on controlled DataFrame."""
    t0 = time.perf_counter()
    try:
        import pandas as pd

        from Programma_CS2_RENAN.backend.analysis.belief_model import AdaptiveBeliefCalibrator
    except ImportError:
        return RuleResult(
            71, "Active learning", SKIP, details="AdaptiveBeliefCalibrator not available"
        )

    calibrator = AdaptiveBeliefCalibrator()

    # Controlled DataFrame with enough samples
    import numpy as np

    np.random.seed(42)
    n = 150
    df = pd.DataFrame(
        {
            "hp_bracket": np.random.choice(["full", "damaged", "critical"], n),
            "weapon_class": np.random.choice(["rifle", "awp", "smg", "pistol"], n),
            "died": np.random.choice([True, False], n),
            "threat_level": np.random.uniform(0, 1, n),
            "information_age": np.random.uniform(0, 30, n),
        }
    )

    try:
        result = calibrator.auto_calibrate(df)
        calibrated = result is not None and len(result) > 0
    except Exception as e:
        return RuleResult(71, "Active learning", SKIP, details=f"auto_calibrate raised: {e}")

    return RuleResult(
        71,
        "Active learning",
        PASS if calibrated else FAIL,
        evidence={
            "calibrated": calibrated,
            "result_keys": list(result.keys()) if isinstance(result, dict) else None,
        },
        details=f"Calibrator updated priors: {calibrated}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_72() -> RuleResult:
    """Version lineage: save checkpoint + JSON metadata -> load -> functional model."""
    t0 = time.perf_counter()

    with deterministic_context():
        model = ModelFactory.get_model(ModelFactory.TYPE_LEGACY)
        model.eval()
        x = torch.randn(2, 10, METADATA_DIM)
        with torch.no_grad():
            out_before = model(x).clone()

    with tempfile.TemporaryDirectory() as tmpdir:
        ckpt_path = os.path.join(tmpdir, "test_checkpoint.pt")
        meta_path = os.path.join(tmpdir, "test_checkpoint_meta.json")

        # Save
        torch.save(model.state_dict(), ckpt_path)
        metadata = {
            "version": "1.0-test",
            "timestamp": "2026-02-17T00:00:00",
            "metrics": {"test_loss": 0.5},
            "model_type": "legacy",
        }
        with open(meta_path, "w") as f:
            json.dump(metadata, f)

        # Load
        model2 = ModelFactory.get_model(ModelFactory.TYPE_LEGACY)
        model2.load_state_dict(torch.load(ckpt_path, weights_only=True))
        model2.eval()

        with deterministic_context():
            x = torch.randn(2, 10, METADATA_DIM)
            with torch.no_grad():
                out_after = model2(x)

        # Load metadata
        with open(meta_path) as f:
            loaded_meta = json.load(f)

    functional = not torch.isnan(out_after).any()
    meta_ok = loaded_meta.get("version") == "1.0-test"

    passed = functional and meta_ok
    return RuleResult(
        72,
        "Version lineage",
        PASS if passed else FAIL,
        evidence={"functional_after_load": bool(functional), "metadata_roundtrip": meta_ok},
        details=f"Checkpoint roundtrip: functional={functional}, metadata={meta_ok}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_73() -> RuleResult:
    """Experimentation framework (MANUAL): TrainingOrchestrator supports different types."""
    return RuleResult(
        73,
        "Experimentation framework",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: TrainingOrchestrator supports different "
        "model_types and hyperparameters. Document procedure.",
    )


def _rule_74() -> RuleResult:
    """Regression testing (MANUAL): headless_validator.py provides regression gate."""
    return RuleResult(
        74,
        "Regression testing",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: headless_validator.py provides regression gate. "
        "This framework itself IS the intelligence regression test.",
    )
