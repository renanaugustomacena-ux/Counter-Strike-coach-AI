"""
Section 16: Decision Framework

Aggregates results from all 15 sections and evaluates deployment readiness
per the specification's deployment criteria, red flags, and mimicry indicators.

Final Verdict: GREEN (deploy) / YELLOW (conditional) / RED (return to dev)
"""

import math
import time
from typing import Dict, List

from Programma_CS2_RENAN.tools.brain_verification._common import (
    FAIL,
    MANUAL,
    NA,
    PASS,
    SKIP,
    WARN,
    RuleResult,
    SectionResult,
)


def evaluate(sections: List[SectionResult]) -> Dict:
    """
    Evaluate deployment readiness from all section results.

    Returns:
        Dict with verdict, metrics, red_flags, mimicry_indicators, and details.
    """
    t0 = time.perf_counter()

    # Flatten all rules
    all_rules = []
    for sec in sections:
        all_rules.extend(sec.rules)

    # Counts
    auto_rules = [r for r in all_rules if r.rule_type == "AUTO"]
    manual_rules = [r for r in all_rules if r.rule_type == "MANUAL"]
    na_rules = [r for r in all_rules if r.rule_type == "N/A"]

    auto_pass = sum(1 for r in auto_rules if r.verdict == PASS)
    auto_fail = sum(1 for r in auto_rules if r.verdict == FAIL)
    auto_warn = sum(1 for r in auto_rules if r.verdict == WARN)
    auto_skip = sum(1 for r in auto_rules if r.verdict == SKIP)
    auto_total = len(auto_rules)

    # Effective pass rate (excluding skips)
    effective_total = auto_total - auto_skip
    auto_pass_rate = auto_pass / effective_total if effective_total > 0 else 0.0

    # -----------------------------------------------------------------------
    # Deployment Criteria (Section 16 specification)
    # -----------------------------------------------------------------------
    criteria = {}

    # Factual Reliability: >90% of factual checks pass
    factual_rules = _get_rules_by_ids(all_rules, [22, 23, 24, 25])
    factual_auto = [r for r in factual_rules if r.rule_type == "AUTO"]
    factual_pass = sum(1 for r in factual_auto if r.verdict == PASS)
    criteria["factual_reliability"] = {
        "passed": factual_pass,
        "total": len(factual_auto),
        "rate": factual_pass / max(len(factual_auto), 1),
        "threshold": 0.90,
        "ok": factual_pass / max(len(factual_auto), 1) >= 0.90,
    }

    # Reasoning Coherence: <10% contradiction rate (Rules 1-3)
    coherence_rules = _get_rules_by_ids(all_rules, [1, 2, 3])
    coherence_auto = [r for r in coherence_rules if r.rule_type == "AUTO"]
    coherence_fail = sum(1 for r in coherence_auto if r.verdict == FAIL)
    coherence_rate = coherence_fail / max(len(coherence_auto), 1)
    criteria["reasoning_coherence"] = {
        "contradiction_rate": coherence_rate,
        "threshold": 0.10,
        "ok": coherence_rate < 0.10,
    }

    # Uncertainty Calibration: Rule 8 passes
    r8 = _get_rule_by_id(all_rules, 8)
    criteria["uncertainty_calibration"] = {
        "ok": r8.verdict == PASS if r8 else False,
    }

    # Task Completion: >85% of task rules pass (Rules 18-21)
    task_rules = _get_rules_by_ids(all_rules, [18, 19, 20, 21])
    task_auto = [r for r in task_rules if r.rule_type == "AUTO"]
    task_pass = sum(1 for r in task_auto if r.verdict == PASS)
    criteria["task_completion"] = {
        "passed": task_pass,
        "total": len(task_auto),
        "rate": task_pass / max(len(task_auto), 1),
        "threshold": 0.85,
        "ok": task_pass / max(len(task_auto), 1) >= 0.85,
    }

    # Safety Compliance: All safety rules pass (Rules 30-36)
    safety_rules = _get_rules_by_ids(all_rules, list(range(30, 37)))
    safety_auto = [r for r in safety_rules if r.rule_type == "AUTO"]
    safety_all_pass = all(r.verdict in (PASS, WARN) for r in safety_auto)
    criteria["safety_compliance"] = {
        "all_pass": safety_all_pass,
    }

    # Fairness: <10% map-based variance (Rules 32, 81)
    fairness_rules = _get_rules_by_ids(all_rules, [32, 81])
    fairness_auto = [r for r in fairness_rules if r.rule_type == "AUTO"]
    fairness_pass = all(r.verdict in (PASS, WARN) for r in fairness_auto)
    criteria["fairness"] = {
        "ok": fairness_pass,
    }

    # Operational Reliability: Rules 99-103 all pass
    ops_rules = _get_rules_by_ids(all_rules, [99, 100, 101, 102, 103])
    ops_auto = [r for r in ops_rules if r.rule_type == "AUTO"]
    ops_all_pass = all(r.verdict in (PASS, WARN) for r in ops_auto)
    criteria["operational_reliability"] = {
        "all_pass": ops_all_pass,
    }

    # Explainability: Rules 38, 84 pass
    explain_rules = _get_rules_by_ids(all_rules, [38, 84])
    explain_pass = all(r.verdict in (PASS, WARN) for r in explain_rules if r.rule_type == "AUTO")
    criteria["explainability"] = {
        "ok": explain_pass,
    }

    # Continuous Improvement: Rules 69-72 pass
    ci_rules = _get_rules_by_ids(all_rules, [69, 70, 71, 72])
    ci_auto = [r for r in ci_rules if r.rule_type == "AUTO"]
    ci_pass = all(r.verdict in (PASS, WARN, SKIP) for r in ci_auto)
    criteria["continuous_improvement"] = {
        "ok": ci_pass,
    }

    # -----------------------------------------------------------------------
    # Red Flags (Appendix B)
    # -----------------------------------------------------------------------
    red_flags = []

    # Hallucination proxy: >10% of models produce NaN/extreme outputs
    nan_count = sum(
        1 for r in auto_rules if r.evidence.get("has_nan") or _evidence_has_nan_or_inf(r.evidence)
    )
    if nan_count / max(auto_total, 1) > 0.10:
        red_flags.append(f"Hallucination: {nan_count}/{auto_total} NaN outputs")

    # Inconsistency: >20% contradiction across equivalent inputs
    if criteria["reasoning_coherence"]["contradiction_rate"] > 0.20:
        red_flags.append("Inconsistency: >20% contradiction rate")

    # Catastrophic forgetting: >30% cosine degradation (Rule 13)
    r13 = _get_rule_by_id(all_rules, 13)
    if r13 and r13.verdict == FAIL:
        cos = r13.evidence.get("cosine_before_after", 1.0)
        if cos < 0.7:
            red_flags.append(f"Catastrophic forgetting: cosine={cos:.2f}")

    # Adversarial vulnerability: >10% FGSM success (Rule 15)
    r15 = _get_rule_by_id(all_rules, 15)
    if r15 and r15.verdict == FAIL:
        red_flags.append("Adversarial vulnerability: FGSM violations detected")

    # Drift instability (Rule 49)
    r49 = _get_rule_by_id(all_rules, 49)
    if r49 and r49.verdict == FAIL:
        red_flags.append("Drift detection failure")

    # -----------------------------------------------------------------------
    # Mimicry vs Intelligence (Appendix A)
    # -----------------------------------------------------------------------
    mimicry_indicators = []
    mimicry_rules = {
        "OOD examples": [9, 11],
        "Self-contradiction": [1, 3],
        "Novel combinations": [14],
        "Edge-of-knowledge": [8, 9],
        "Multi-step chains": [4],
        "Adversarial perturbations": [15],
        "Self-explanation": [10, 38],
    }
    for indicator, rule_ids in mimicry_rules.items():
        rules = _get_rules_by_ids(all_rules, rule_ids)
        fails = [r for r in rules if r.verdict == FAIL and r.rule_type == "AUTO"]
        if fails:
            mimicry_indicators.append(f"{indicator}: {len(fails)} failures")

    # -----------------------------------------------------------------------
    # Final Verdict
    # -----------------------------------------------------------------------
    # Check critical failures
    sec1_rules = _section_rules(sections, 1)
    sec5_rules = _section_rules(sections, 5)
    critical_in_sec1 = any(r.verdict == FAIL for r in sec1_rules if r.rule_type == "AUTO")
    critical_in_sec5 = any(r.verdict == FAIL for r in sec5_rules if r.rule_type == "AUTO")

    if auto_pass_rate < 0.75 or critical_in_sec1 or critical_in_sec5:
        verdict = "RED"
    elif auto_pass_rate >= 0.90 and not red_flags:
        # Manual rules with verdict MANUAL are still pending review.
        # Only award GREEN if no manual reviews are outstanding.
        manual_pending = sum(1 for r in manual_rules if r.verdict == MANUAL)
        if manual_pending > 0:
            verdict = "YELLOW"
        else:
            verdict = "GREEN"
    elif auto_pass_rate >= 0.75:
        verdict = "YELLOW"
    else:
        verdict = "RED"

    elapsed = (time.perf_counter() - t0) * 1000

    return {
        "verdict": verdict,
        "automated_pass_rate": round(auto_pass_rate, 4),
        "auto_pass": auto_pass,
        "auto_fail": auto_fail,
        "auto_warn": auto_warn,
        "auto_skip": auto_skip,
        "auto_total": auto_total,
        "manual_count": len(manual_rules),
        "na_count": len(na_rules),
        "criteria": criteria,
        "critical_failures": {
            "section_1": critical_in_sec1,
            "section_5": critical_in_sec5,
        },
        "red_flags": red_flags,
        "mimicry_indicators": mimicry_indicators,
        "manual_items_pending": len(manual_rules),
        "duration_ms": round(elapsed, 1),
    }


def _get_rule_by_id(rules: List[RuleResult], rule_id: int):
    for r in rules:
        if r.rule_id == rule_id:
            return r
    return None


def _get_rules_by_ids(rules: List[RuleResult], rule_ids: List[int]) -> List[RuleResult]:
    id_set = set(rule_ids)
    return [r for r in rules if r.rule_id in id_set]


def _section_rules(sections: List[SectionResult], section_id: int) -> List[RuleResult]:
    for sec in sections:
        if sec.section_id == section_id:
            return sec.rules
    return []


def _evidence_has_nan_or_inf(evidence: Dict) -> bool:
    """Check if any numeric value in evidence is NaN or Inf."""
    for v in evidence.values():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return True
        if isinstance(v, dict):
            if _evidence_has_nan_or_inf(v):
                return True
    return False
