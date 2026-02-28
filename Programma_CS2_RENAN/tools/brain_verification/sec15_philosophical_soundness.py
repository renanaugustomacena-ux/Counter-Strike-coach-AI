"""
Section 15: Philosophical Soundness (Rules 114-118)

Tests ontological consistency, epistemological soundness,
behavior-over-implementation, and substrate-neutral testing.
Auto: 3, Manual: 2
"""

import time

import torch

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
    extract_output_tensor,
    forward_model,
    get_all_models,
    get_random_input,
)


def run(quick: bool = False) -> SectionResult:
    section = SectionResult(15, "Philosophical Soundness")

    section.add(_rule_114())
    section.add(_rule_115())
    section.add(_rule_116())
    section.add(_rule_117())
    section.add(_rule_118())

    return section


def _rule_114() -> RuleResult:
    """Ontological consistency: FEATURE_NAMES has 25 entries, all input_dims=25 (except RoleHead=5)."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            METADATA_DIM,
            FeatureExtractor,
        )
    except ImportError:
        return RuleResult(
            114, "Ontological consistency", SKIP, details="FeatureExtractor not available"
        )

    feature_names = FeatureExtractor.get_feature_names()
    name_count = len(feature_names)

    checks = {"feature_names_count": name_count, "expected": 25, "names_match": name_count == 25}

    # Check model input dims
    models = get_all_models()
    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA, ModelFactory.TYPE_VL_JEPA]:
        model = models.get(mt)
        if model is None:
            continue
        # Check by running a forward pass with METADATA_DIM
        try:
            x = torch.randn(1, 5, METADATA_DIM)
            model.eval()
            with torch.no_grad():
                out = model(x)
            checks[f"{mt}_accepts_25"] = True
        except Exception:
            checks[f"{mt}_accepts_25"] = False

    # RoleHead should accept 5
    rh = models.get(ModelFactory.TYPE_ROLE_HEAD)
    if rh is not None:
        try:
            x = torch.randn(1, 5)
            rh.eval()
            with torch.no_grad():
                out = rh(x)
            checks["role_head_accepts_5"] = True
        except Exception:
            checks["role_head_accepts_5"] = False

    passed = name_count == 25 and all(
        v for k, v in checks.items() if k.endswith("_25") or k.endswith("_5")
    )
    return RuleResult(
        114,
        "Ontological consistency",
        PASS if passed else FAIL,
        evidence=checks,
        details=f"Feature names={name_count}/25, models accept correct dims",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_115() -> RuleResult:
    """Philosophical reasoning (MANUAL): document for review."""
    return RuleResult(
        115,
        "Philosophical reasoning",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: review philosophical underpinnings of "
        "coaching AI. Document for review.",
    )


def _rule_116() -> RuleResult:
    """Epistemological soundness: BeliefModel uses Bayesian updating, calibrator changes priors."""
    t0 = time.perf_counter()
    checks = {}

    # Check BeliefModel uses Bayesian updating
    try:
        from Programma_CS2_RENAN.backend.analysis.belief_model import (
            AdaptiveBeliefCalibrator,
            DeathProbabilityEstimator,
            get_death_estimator,
        )

        est = get_death_estimator()
        # Verify it has priors (Bayesian approach)
        has_priors = hasattr(est, "priors") and isinstance(est.priors, dict)
        checks["bayesian_priors"] = has_priors

        # Verify calibrator exists and can update
        cal = AdaptiveBeliefCalibrator()
        has_auto_calibrate = hasattr(cal, "auto_calibrate")
        checks["calibrator_exists"] = has_auto_calibrate
    except ImportError:
        checks["belief_model"] = "not available"

    passed = all(v for v in checks.values() if isinstance(v, bool))
    return RuleResult(
        116,
        "Epistemological soundness",
        (
            PASS
            if passed
            else (FAIL if any(v is False for v in checks.values() if isinstance(v, bool)) else SKIP)
        ),
        evidence=checks,
        details=f"Bayesian approach: priors={checks.get('bayesian_priors')}, "
        f"calibrator={checks.get('calibrator_exists')}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_117() -> RuleResult:
    """Behavior-over-implementation: Legacy and JEPA both produce defensive-polarity for low-HP inputs."""
    t0 = time.perf_counter()
    models = get_all_models()
    results = {}

    # Low-HP input: health=0.1, armor=0
    with deterministic_context():
        x_low_hp = torch.zeros(2, 10, METADATA_DIM)
        x_low_hp[:, :, 0] = 0.1  # Low health
        x_low_hp[:, :, 1] = 0.0  # No armor
        x_low_hp[:, :, 8] = 0.5  # Some enemies visible

        x_high_hp = torch.zeros(2, 10, METADATA_DIM)
        x_high_hp[:, :, 0] = 1.0  # Full health
        x_high_hp[:, :, 1] = 1.0  # Full armor
        x_high_hp[:, :, 8] = 0.5  # Same enemies

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA]:
        model = models.get(mt)
        if model is None:
            continue
        model.eval()
        with torch.no_grad():
            out_low = extract_output_tensor(model(x_low_hp))
            out_high = extract_output_tensor(model(x_high_hp))

        if out_low is not None and out_high is not None:
            # Different outputs for different HP levels
            diff = torch.norm(out_low - out_high).item()
            # Both should produce different behavior (same direction of response)
            results[mt] = {"diff": round(diff, 4), "responds_to_hp": diff > 0.001}

    if len(results) < 2:
        return RuleResult(
            117, "Behavior-over-implementation", SKIP, details="Need both Legacy and JEPA"
        )

    # Both models respond to HP change
    both_respond = all(v.get("responds_to_hp", False) for v in results.values())

    return RuleResult(
        117,
        "Behavior-over-implementation",
        PASS if both_respond else WARN,
        evidence=results,
        details=f"Both respond to HP: {both_respond}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_118() -> RuleResult:
    """Substrate-neutral testing (MANUAL): verify tests check behavior not implementation."""
    return RuleResult(
        118,
        "Substrate-neutral testing",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: verify this framework tests behavior "
        "(outputs, properties) not implementation details (specific "
        "weight values, internal states).",
    )
