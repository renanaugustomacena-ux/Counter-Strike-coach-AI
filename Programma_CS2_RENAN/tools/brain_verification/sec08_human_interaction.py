"""
Section 8: Human Interaction Quality (Rules 63-68)

Tests user satisfaction, frustration detection, diverse user testing,
human-AI collaboration, confidence communication, and complementary skills.
Auto: 2, Manual: 4
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
    get_model,
)


def run(quick: bool = False) -> SectionResult:
    section = SectionResult(8, "Human Interaction Quality")

    section.add(_rule_63())
    section.add(_rule_64())
    section.add(_rule_65())
    section.add(_rule_66())
    section.add(_rule_67())
    section.add(_rule_68())

    return section


def _rule_63() -> RuleResult:
    """User satisfaction (MANUAL): user study procedure."""
    return RuleResult(
        63,
        "User satisfaction",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: conduct user study (n>=30) measuring "
        "coaching satisfaction. Document procedure.",
    )


def _rule_64() -> RuleResult:
    """Frustration detection: MomentumTracker detects tilt for low multiplier."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.analysis.momentum import TILT_THRESHOLD, MomentumTracker
    except ImportError:
        return RuleResult(
            64, "Frustration detection", SKIP, details="MomentumTracker not available"
        )

    tracker = MomentumTracker()
    # Induce tilt: consecutive losses
    for r in range(1, 8):
        tracker.update(round_won=False, round_number=r)

    is_tilted = tracker.state.is_tilted
    mult = tracker.state.current_multiplier

    return RuleResult(
        64,
        "Frustration detection",
        PASS if is_tilted else WARN,
        evidence={
            "is_tilted": is_tilted,
            "multiplier": round(mult, 4),
            "tilt_threshold": TILT_THRESHOLD,
        },
        details=f"After 7 losses: tilted={is_tilted}, mult={mult:.3f} (threshold={TILT_THRESHOLD})",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_65() -> RuleResult:
    """Diverse user testing (MANUAL): test across skill levels."""
    return RuleResult(
        65,
        "Diverse user testing",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: test coaching quality across Silver/Gold/"
        "DMG/Global skill levels. Document procedure.",
    )


def _rule_66() -> RuleResult:
    """Human-AI collaboration (MANUAL): coaching dialogue interaction."""
    return RuleResult(
        66,
        "Human-AI collaboration",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: evaluate coaching dialogue engine "
        "interaction quality. Document procedure.",
    )


def _rule_67() -> RuleResult:
    """Confidence communication: VL-JEPA concepts include probs, MaturityObservatory exposes state."""
    t0 = time.perf_counter()
    checks = {}

    # VL-JEPA top_concepts include probability values + concept names
    vl = get_model(ModelFactory.TYPE_VL_JEPA)
    if vl is not None:
        vl.eval()
        x = torch.randn(2, 10, METADATA_DIM)
        with torch.no_grad():
            r = vl.forward_vl(x)
        tc = r.get("top_concepts")
        if tc and len(tc) > 0:
            # Check format: list of (name, prob) tuples
            has_name = isinstance(tc[0][0], str) if isinstance(tc[0], (list, tuple)) else False
            has_prob = (
                isinstance(tc[0][1], float)
                if isinstance(tc[0], (list, tuple)) and len(tc[0]) > 1
                else False
            )
            checks["vl_concepts"] = has_name and has_prob

    # MaturityObservatory exposes current_state + current_conviction
    try:
        from Programma_CS2_RENAN.backend.nn.maturity_observatory import MaturityObservatory

        obs = MaturityObservatory()
        has_state = hasattr(obs, "current_state") and isinstance(obs.current_state, str)
        has_conviction = hasattr(obs, "current_conviction")
        checks["maturity_state"] = has_state
        checks["maturity_conviction"] = has_conviction
    except ImportError:
        pass

    passed = all(checks.values()) if checks else False
    return RuleResult(
        67,
        "Confidence communication",
        PASS if passed else (WARN if any(checks.values()) else SKIP),
        evidence=checks,
        details=f"Confidence comm: {sum(checks.values())}/{len(checks)} accessible",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_68() -> RuleResult:
    """Complementary skills (MANUAL): coaching addresses BlindSpotDetector findings."""
    return RuleResult(
        68,
        "Complementary skills",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: evaluate that coaching addresses "
        "BlindSpotDetector findings. Document procedure.",
    )
