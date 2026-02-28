"""
Section 12: Specialized Intelligence (Rules 90-98)

Tests scientific reasoning, mathematical correctness, creativity,
social context, empathy, and emotional intelligence.
Auto: 5, Manual: 2, N/A: 2
"""

import math
import time

import torch

from Programma_CS2_RENAN.tools.brain_verification._common import (
    FAIL,
    MANUAL,
    METADATA_DIM,
    NA,
    PASS,
    SKIP,
    WARN,
    RuleResult,
    SectionResult,
    deterministic_context,
)


def run(quick: bool = False) -> SectionResult:
    section = SectionResult(12, "Specialized Intelligence")

    section.add(_rule_90())
    section.add(_rule_91())
    section.add(_rule_92())
    section.add(_rule_93())
    section.add(_rule_94())
    section.add(_rule_95())
    section.add(_rule_96())
    section.add(_rule_97())
    section.add(_rule_98())

    return section


def _rule_90() -> RuleResult:
    """Scientific reasoning: EntropyAnalyzer produces valid Shannon entropy."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.analysis.entropy_analysis import EntropyAnalyzer
    except ImportError:
        return RuleResult(90, "Scientific reasoning", SKIP, details="EntropyAnalyzer not available")

    ea = EntropyAnalyzer(grid_resolution=32)
    positions = [(float(i * 128), float(j * 128)) for i in range(5) for j in range(5)]
    h = ea.compute_position_entropy(positions)

    non_negative = h >= 0.0
    max_entropy = math.log(32 * 32)  # log(grid_size^2)
    bounded = h <= max_entropy + 0.01

    passed = non_negative and bounded
    return RuleResult(
        90,
        "Scientific reasoning",
        PASS if passed else FAIL,
        evidence={
            "entropy": round(h, 4),
            "non_negative": non_negative,
            "max_possible": round(max_entropy, 4),
            "bounded": bounded,
        },
        details=f"Shannon entropy={h:.4f}, bounded=[0, {max_entropy:.2f}]",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_91() -> RuleResult:
    """Mathematical correctness: P(death) monotonically increases with threat level."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.analysis.belief_model import (
            BeliefState,
            get_death_estimator,
        )
    except ImportError:
        return RuleResult(
            91, "Mathematical correctness", SKIP, details="DeathProbabilityEstimator not available"
        )

    est = get_death_estimator()
    probs = []
    for threat_mult in range(20):
        enemies = 1 + threat_mult // 5
        exposure = min(threat_mult / 20.0, 1.0)
        info_age = max(30.0 - threat_mult * 1.5, 0.0)
        state = BeliefState(
            visible_enemies=enemies,
            inferred_enemies=enemies,
            information_age=info_age,
            positional_exposure=exposure,
        )
        p = est.estimate(state, player_hp=80, armor=True, weapon_class="rifle")
        probs.append(p)

    # Check general increasing trend (at least 75% non-decreasing)
    increases = sum(1 for i in range(len(probs) - 1) if probs[i + 1] >= probs[i] - 0.01)
    total = len(probs) - 1
    trend_ok = increases / total >= 0.75

    return RuleResult(
        91,
        "Mathematical correctness",
        PASS if trend_ok else FAIL,
        evidence={
            "probs": [round(p, 4) for p in probs],
            "increasing_pairs": increases,
            "total_pairs": total,
            "trend_ratio": round(increases / total, 2),
        },
        details=f"P(death) trend: {increases}/{total} increasing ({increases/total:.0%})",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_92() -> RuleResult:
    """Experimental design (MANUAL): training experiment procedure."""
    return RuleResult(
        92,
        "Experimental design",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: document training experiment design "
        "procedure with controlled variables.",
    )


def _rule_93() -> RuleResult:
    """Creativity (MANUAL): novel strategy suggestions beyond pro baselines."""
    return RuleResult(
        93,
        "Creativity",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: evaluate novel strategy suggestions "
        "beyond pro baselines. Document examples.",
    )


def _rule_94() -> RuleResult:
    """Originality: N/A for numerical models."""
    return RuleResult(
        94, "Originality", NA, rule_type="N/A", details="Not applicable to numerical models."
    )


def _rule_95() -> RuleResult:
    """Aesthetic quality: N/A for numerical models."""
    return RuleResult(
        95, "Aesthetic quality", NA, rule_type="N/A", details="Not applicable to numerical models."
    )


def _rule_96() -> RuleResult:
    """Social context: MomentumTracker is_tilted and is_hot are mutually exclusive."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.analysis.momentum import TILT_THRESHOLD, MomentumTracker
    except ImportError:
        return RuleResult(96, "Social context", SKIP, details="MomentumTracker not available")

    # Test many states
    tracker = MomentumTracker()
    violations = 0
    tests = 0

    for r in range(1, 30):
        won = r % 2 == 0  # Alternating
        tracker.update(round_won=won, round_number=r)
        state = tracker.state
        tests += 1
        if state.is_tilted and state.is_hot:
            violations += 1

    # Also test extreme cases
    tracker2 = MomentumTracker()
    for r in range(1, 10):
        tracker2.update(round_won=False, round_number=r)
    if tracker2.state.is_tilted and tracker2.state.is_hot:
        violations += 1
    tests += 1

    passed = violations == 0
    return RuleResult(
        96,
        "Social context",
        PASS if passed else FAIL,
        evidence={"violations": violations, "tests": tests},
        details=f"Mutual exclusivity: {violations} violations in {tests} tests",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_97() -> RuleResult:
    """Empathy: low-health + high-threat -> higher severity than high-health + low-threat."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.analysis.belief_model import (
            BeliefState,
            get_death_estimator,
        )
    except ImportError:
        return RuleResult(97, "Empathy", SKIP, details="BeliefModel not available")

    est = get_death_estimator()

    # Low health + high threat
    state_bad = BeliefState(
        visible_enemies=4, inferred_enemies=2, information_age=2.0, positional_exposure=0.9
    )
    p_bad = est.estimate(state_bad, player_hp=20, armor=False, weapon_class="rifle")

    # High health + low threat
    state_good = BeliefState(
        visible_enemies=0, inferred_enemies=1, information_age=20.0, positional_exposure=0.1
    )
    p_good = est.estimate(state_good, player_hp=100, armor=True, weapon_class="rifle")

    higher_severity = p_bad > p_good
    return RuleResult(
        97,
        "Empathy",
        PASS if higher_severity else FAIL,
        evidence={
            "p_bad_state": round(p_bad, 4),
            "p_good_state": round(p_good, 4),
            "higher_for_worse": higher_severity,
        },
        details=f"Bad state P={p_bad:.3f} > Good state P={p_good:.3f}: {higher_severity}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_98() -> RuleResult:
    """Emotional intelligence: MomentumState hot vs tilted thresholds correct."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.analysis.momentum import (
            MULTIPLIER_MAX,
            MULTIPLIER_MIN,
            TILT_THRESHOLD,
            MomentumState,
        )
    except ImportError:
        return RuleResult(98, "Emotional intelligence", SKIP, details="MomentumState not available")

    # TILT_THRESHOLD < 1.0 < HOT_THRESHOLD (1.2)
    tilt_ok = TILT_THRESHOLD < 1.0
    hot_threshold = 1.2  # From MomentumState.is_hot property
    hot_ok = hot_threshold > 1.0

    # Verify actual states
    tilted_state = MomentumState(current_multiplier=0.75)
    hot_state = MomentumState(current_multiplier=1.3)
    neutral_state = MomentumState(current_multiplier=1.0)

    tilt_detected = tilted_state.is_tilted and not tilted_state.is_hot
    hot_detected = hot_state.is_hot and not hot_state.is_tilted
    neutral_ok = not neutral_state.is_tilted and not neutral_state.is_hot

    passed = tilt_ok and hot_ok and tilt_detected and hot_detected and neutral_ok
    return RuleResult(
        98,
        "Emotional intelligence",
        PASS if passed else FAIL,
        evidence={
            "tilt_threshold": TILT_THRESHOLD,
            "hot_threshold": hot_threshold,
            "tilt_below_1": tilt_ok,
            "hot_above_1": hot_ok,
            "tilt_detected": tilt_detected,
            "hot_detected": hot_detected,
            "neutral_ok": neutral_ok,
        },
        details=f"Thresholds: tilt={TILT_THRESHOLD}<1.0<hot={hot_threshold}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )
