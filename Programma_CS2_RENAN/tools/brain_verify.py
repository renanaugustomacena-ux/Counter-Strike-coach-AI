#!/usr/bin/env python3
"""
AI Brain Verification Framework — 118-rule intelligence quality verification.

Verifies that AI models produce consistent, coherent, generalizable, safe,
and deployment-ready outputs. Sits at the top of the validation hierarchy:

    headless_validator.py      (gate)
    pytest                     (logic)
    backend_validator.py       (build)
    Goliath_Hospital.py        (comprehensive)
    brain_verify.py            (intelligence)  <-- THIS TOOL

Usage:
    python Programma_CS2_RENAN/tools/brain_verify.py
    python Programma_CS2_RENAN/tools/brain_verify.py --section 1
    python Programma_CS2_RENAN/tools/brain_verify.py --quick
    python Programma_CS2_RENAN/tools/brain_verify.py --json

Exit codes: 0 = all automated PASS, 1 = any FAIL
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# F8-27: PROJECT_ROOT/SOURCE_ROOT already set by _infra import side effect — no redundant call needed
from _infra import PROJECT_ROOT, SOURCE_ROOT, BaseValidator, Severity, path_stabilize

from Programma_CS2_RENAN.tools.brain_verification import (
    sec01_foundational_intelligence,
    sec02_learning_adaptation,
    sec03_practical_utility,
    sec04_safety_alignment,
    sec05_architectural_quality,
    sec06_monitoring_observability,
    sec07_domain_specific,
    sec08_human_interaction,
    sec09_continuous_improvement,
    sec10_meta_level,
    sec11_ethical_societal,
    sec12_specialized_domains,
    sec13_deployment_readiness,
    sec14_intelligence_benchmarking,
    sec15_philosophical_soundness,
    sec16_decision_framework,
)
from Programma_CS2_RENAN.tools.brain_verification._common import (
    FAIL,
    MANUAL,
    NA,
    PASS,
    SKIP,
    WARN,
    SectionResult,
)

# Section registry (id, name, module)
SECTIONS = [
    (1, "Foundational Intelligence", sec01_foundational_intelligence),
    (2, "Learning & Adaptation", sec02_learning_adaptation),
    (3, "Practical Utility", sec03_practical_utility),
    (4, "Safety & Alignment", sec04_safety_alignment),
    (5, "Architectural Quality", sec05_architectural_quality),
    (6, "Monitoring & Observability", sec06_monitoring_observability),
    (7, "Domain-Specific Intelligence", sec07_domain_specific),
    (8, "Human Interaction Quality", sec08_human_interaction),
    (9, "Continuous Improvement", sec09_continuous_improvement),
    (10, "Meta-Level Verification", sec10_meta_level),
    (11, "Ethical & Societal Impact", sec11_ethical_societal),
    (12, "Specialized Intelligence", sec12_specialized_domains),
    (13, "Deployment Readiness", sec13_deployment_readiness),
    (14, "Intelligence Benchmarking", sec14_intelligence_benchmarking),
    (15, "Philosophical Soundness", sec15_philosophical_soundness),
]
# F8-17: sec16_decision_framework intentionally excluded from SECTIONS list.
# It aggregates all sections and always runs after the main loop.
# --section 16 CLI flag is a no-op; decision framework always executes.

# Verdict colors
VERDICT_COLORS = {
    PASS: "\033[92m",  # Green
    FAIL: "\033[91m",  # Red
    WARN: "\033[93m",  # Yellow
    SKIP: "\033[90m",  # Gray
    MANUAL: "\033[96m",  # Cyan
    NA: "\033[90m",  # Gray
}
RESET = "\033[0m"


class BrainVerifier(BaseValidator):
    """AI Brain Verification Framework orchestrator."""

    def __init__(self):
        super().__init__("AI Brain Verification Framework", version="1.0")
        self._sections = []
        self._decision = {}
        self._quick = False
        self._target_section = None

    def _add_extra_args(self, parser):
        parser.add_argument(
            "--section", type=int, default=None, help="Run only this section number (1-15)"
        )
        parser.add_argument(
            "--quick", action="store_true", help="Skip training-loop rules for faster execution"
        )

    def define_checks(self):
        self._quick = getattr(self.args, "quick", False)
        self._target_section = getattr(self.args, "section", None)

        total_sections = len(SECTIONS)
        sections_to_run = SECTIONS

        if self._target_section is not None:
            sections_to_run = [(i, n, m) for i, n, m in SECTIONS if i == self._target_section]
            if not sections_to_run:
                print(f"  Section {self._target_section} not found. Valid: 1-{total_sections}")
                return

        for sec_id, sec_name, sec_module in sections_to_run:
            self.console.section(
                f"Section {sec_id}: {sec_name}",
                sec_id,
                total_sections,
            )

            try:
                result = sec_module.run(quick=self._quick)
                self._sections.append(result)

                # Register each rule with the base validator
                for rule in result.rules:
                    if rule.rule_type in ("MANUAL", "N/A"):
                        # Manual/N/A: show as info, don't count toward pass/fail
                        self.check(
                            f"S{sec_id}",
                            f"Rule {rule.rule_id}: {rule.name}",
                            True,
                            detail=f"[{rule.verdict}] {rule.details}",
                            severity=Severity.INFO,
                        )
                    elif rule.verdict == PASS:
                        self.check(
                            f"S{sec_id}",
                            f"Rule {rule.rule_id}: {rule.name}",
                            True,
                            detail=rule.details,
                        )
                    elif rule.verdict == WARN:
                        self.check(
                            f"S{sec_id}",
                            f"Rule {rule.rule_id}: {rule.name}",
                            True,           # F8-02: WARN is not a FAIL — preserves exit code 0
                            error=rule.details,
                            severity=Severity.WARNING,
                        )
                    elif rule.verdict == SKIP:
                        self.check(
                            f"S{sec_id}",
                            f"Rule {rule.rule_id}: {rule.name}",
                            True,
                            detail=f"[SKIP] {rule.details}",
                            severity=Severity.INFO,
                        )
                    else:  # FAIL
                        self.check(
                            f"S{sec_id}",
                            f"Rule {rule.rule_id}: {rule.name}",
                            False,
                            error=rule.details,
                            severity=Severity.ERROR,
                        )
            except Exception as e:
                self.check(
                    f"S{sec_id}",
                    f"Section {sec_id} execution",
                    False,
                    error=f"Section crashed: {e}",
                    severity=Severity.CRITICAL,
                )

        # Decision Framework (always runs)
        if self._sections:
            self.console.section("Decision Framework", 16, 16)
            self._decision = sec16_decision_framework.evaluate(self._sections)
            verdict = self._decision.get("verdict", "RED")

            color = {
                "GREEN": "\033[92m",
                "YELLOW": "\033[93m",
                "RED": "\033[91m",
            }.get(verdict, "")

            print(f"\n  Deployment Verdict: {color}{verdict}{RESET}")
            print(f"  Automated Pass Rate: {self._decision.get('automated_pass_rate', 0):.1%}")
            print(
                f"  Auto: {self._decision.get('auto_pass', 0)} pass, "
                f"{self._decision.get('auto_fail', 0)} fail, "
                f"{self._decision.get('auto_warn', 0)} warn, "
                f"{self._decision.get('auto_skip', 0)} skip"
            )
            print(f"  Manual Items Pending: {self._decision.get('manual_items_pending', 0)}")

            if self._decision.get("red_flags"):
                print(f"\n  Red Flags:")
                for flag in self._decision["red_flags"]:
                    print(f"    \033[91m!\033[0m {flag}")

            if self._decision.get("mimicry_indicators"):
                print(f"\n  Mimicry Indicators:")
                for ind in self._decision["mimicry_indicators"]:
                    print(f"    \033[93m?\033[0m {ind}")

    def _build_json_report(self) -> dict:
        """Build the full JSON report structure."""
        return {
            "framework_version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(self.report.elapsed_s, 1),
            "summary": {
                "total_rules": 118,
                "automated": self._decision.get("auto_total", 0),
                "manual": self._decision.get("manual_count", 0),
                "not_applicable": self._decision.get("na_count", 0),
                "passed": self._decision.get("auto_pass", 0),
                "failed": self._decision.get("auto_fail", 0),
                "warned": self._decision.get("auto_warn", 0),
                "skipped": self._decision.get("auto_skip", 0),
                "deployment_verdict": self._decision.get("verdict", "RED"),
            },
            "sections": [sec.to_dict() for sec in self._sections],
            "decision_framework": self._decision,
        }

    def run(self) -> int:
        """Override run to also save JSON report."""
        exit_code = super().run()

        # Save JSON report
        if self._sections:
            reports_dir = PROJECT_ROOT / "reports"
            reports_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = reports_dir / f"brain_verification_{timestamp}.json"

            report_data = self._build_json_report()
            with open(report_path, "w") as f:
                json.dump(report_data, f, indent=2, default=str)

            print(f"\n  JSON report saved: {report_path}")

            # Also print JSON to stdout if --json flag
            if getattr(self.args, "json", False):
                print("\n" + json.dumps(report_data, indent=2, default=str))

        return exit_code


if __name__ == "__main__":
    verifier = BrainVerifier()
    sys.exit(verifier.run())
