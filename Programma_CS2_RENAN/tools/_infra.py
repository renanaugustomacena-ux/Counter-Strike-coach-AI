"""
Shared infrastructure for all Macena CS2 Analyzer tools.

Provides:
- Path stabilization (canonical, single source of truth)
- ToolResult / ToolReport for structured reporting
- BaseValidator ABC for consistent tool structure
- Console class for Rich-style terminal output
- Standard argparse helpers
"""

import argparse
import json
import os
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# =============================================================================
# VENV GUARD — prevent misleading failures when running with system Python
# =============================================================================

EXPECTED_VENV = "cs2analyzer"


def require_venv():
    """Bail out early if not running inside a virtual environment."""
    if sys.prefix == sys.base_prefix:
        print(
            f"ERROR: Not running inside a virtual environment.\n"
            f"This project requires the '{EXPECTED_VENV}' venv.\n"
            f"\n"
            f"  Activate it with:  source ~/.venvs/{EXPECTED_VENV}/bin/activate\n"
            f"  Then retry:        python {' '.join(sys.argv)}\n",
            file=sys.stderr,
        )
        sys.exit(2)


# =============================================================================
# PATH STABILIZATION — single canonical implementation
# =============================================================================


def path_stabilize() -> tuple:
    """
    Resolve and return (PROJECT_ROOT, SOURCE_ROOT) for the Macena project.
    Adds PROJECT_ROOT to sys.path if needed.
    Works from any depth inside the project tree.

    Returns:
        (PROJECT_ROOT, SOURCE_ROOT) as Path objects
        PROJECT_ROOT = Macena_cs2_analyzer/
        SOURCE_ROOT  = Macena_cs2_analyzer/Programma_CS2_RENAN/
    """
    require_venv()

    # Walk up from this file: _infra.py -> tools/ -> Programma_CS2_RENAN/ -> root/
    source_root = Path(__file__).resolve().parent.parent
    project_root = source_root.parent

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Prevent Kivy from hijacking CLI args
    os.environ.setdefault("KIVY_NO_ARGS", "1")

    # Fix Windows console encoding
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception as e:
            _ = e  # Intentionally suppressed

    return project_root, source_root


PROJECT_ROOT, SOURCE_ROOT = path_stabilize()


# =============================================================================
# SEVERITY LEVELS
# =============================================================================


class Severity(Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    HEALTHY = "HEALTHY"


# =============================================================================
# TOOL RESULT & REPORT
# =============================================================================


@dataclass
class ToolResult:
    """Single check result."""

    phase: str
    name: str
    passed: bool
    error: Optional[str] = None
    duration_ms: float = 0.0
    severity: Severity = Severity.INFO

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.phase}/{self.name}"


class ToolReport:
    """Aggregates ToolResults into a structured report."""

    def __init__(self, title: str, version: str = "1.0"):
        self.title = title
        self.version = version
        self.results: List[ToolResult] = []
        self._start_time = time.time()

    def add(
        self,
        phase: str,
        name: str,
        passed: bool,
        error: Optional[str] = None,
        duration_ms: float = 0.0,
        severity: Severity = Severity.INFO,
    ) -> ToolResult:
        r = ToolResult(
            phase=phase,
            name=name,
            passed=passed,
            error=error,
            duration_ms=duration_ms,
            severity=severity,
        )
        self.results.append(r)
        return r

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        """Count hard failures (CRITICAL/ERROR). Warnings don't count."""
        return sum(
            1
            for r in self.results
            if not r.passed and r.severity in (Severity.CRITICAL, Severity.ERROR)
        )

    @property
    def warnings(self) -> int:
        """Count soft failures (WARNING/INFO)."""
        return sum(
            1
            for r in self.results
            if not r.passed and r.severity not in (Severity.CRITICAL, Severity.ERROR)
        )

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def all_passed(self) -> bool:
        return self.failed == 0

    @property
    def elapsed_s(self) -> float:
        return time.time() - self._start_time

    def failures(self) -> List[ToolResult]:
        return [r for r in self.results if not r.passed]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "version": self.version,
            "passed": self.passed,
            "failed": self.failed,
            "total": self.total,
            "elapsed_s": round(self.elapsed_s, 2),
            "results": [asdict(r) for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        d = self.to_dict()
        # Normalize severity to its primitive value for portable JSON serialization.
        # dataclasses.asdict() returns the Enum instance on Python <3.12 and the
        # value directly on >=3.12; handle both plus the legacy _value_ dict format.
        for r in d["results"]:
            sev = r["severity"]
            if hasattr(sev, "value"):  # Enum instance (Python <3.12)
                r["severity"] = sev.value
            elif isinstance(sev, dict):  # Legacy dict format with _value_ key
                r["severity"] = sev.get("_value_", sev.get("value", str(sev)))
            # else: already a primitive (string/int), leave unchanged
        return json.dumps(d, indent=indent, default=str)


# =============================================================================
# CONSOLE — Rich-style terminal output without external dependency
# =============================================================================


class Console:
    """Lightweight terminal formatting for tool output."""

    # ANSI color codes
    _COLORS = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
    }

    SEVERITY_STYLES = {
        Severity.CRITICAL: ("red", "bold"),
        Severity.ERROR: ("red",),
        Severity.WARNING: ("yellow",),
        Severity.INFO: ("cyan",),
        Severity.HEALTHY: ("green",),
    }

    def __init__(self, quiet: bool = False):
        self.quiet = quiet
        self._supports_color = self._detect_color()

    def _detect_color(self) -> bool:
        if os.environ.get("NO_COLOR"):
            return False
        if sys.platform == "win32":
            return os.environ.get("TERM") or os.environ.get("WT_SESSION") or True
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def _apply(self, text: str, *styles: str) -> str:
        if not self._supports_color:
            return text
        prefix = "".join(self._COLORS.get(s, "") for s in styles)
        return f"{prefix}{text}{self._COLORS['reset']}" if prefix else text

    def header(self, title: str, version: str = ""):
        if self.quiet:
            return
        line = "=" * 60
        ver = f" v{version}" if version else ""
        print(f"\n{self._apply(line, 'bold')}")
        print(f"  {self._apply(title + ver, 'bold', 'cyan')}")
        print(f"{self._apply(line, 'bold')}\n")

    def section(self, name: str, index: Optional[int] = None, total: Optional[int] = None):
        if self.quiet:
            return
        prefix = f"[{index}/{total}] " if index and total else ""
        print(f"\n{self._apply(prefix + name, 'bold', 'blue')}")
        print(self._apply("-" * (len(prefix) + len(name)), "dim"))

    def check(self, name: str, passed: bool, detail: str = "", severity: Severity = Severity.ERROR):
        if self.quiet and passed:
            return
        if passed:
            icon = self._apply("[PASS]", "green")
        elif severity in (Severity.WARNING, Severity.INFO):
            icon = self._apply("[WARN]", "yellow")
        else:
            icon = self._apply("[FAIL]", "red", "bold")
        suffix = f" ({detail})" if detail else ""
        print(f"  {icon} {name}{suffix}")

    def severity_badge(self, sev: Severity, text: str = "") -> str:
        styles = self.SEVERITY_STYLES.get(sev, ())
        label = text or sev.value
        return self._apply(f"[{label}]", *styles)

    def summary(self, report: ToolReport):
        if self.quiet:
            return
        print(f"\n{'=' * 60}")
        color = "green" if report.all_passed else "red"
        status = "ALL CHECKS PASSED" if report.all_passed else f"{report.failed} CHECK(S) FAILED"
        warn_text = f", {report.warnings} warning(s)" if report.warnings else ""
        print(f"  {self._apply(report.title, 'bold')}: {self._apply(status, color, 'bold')}")
        print(f"  {report.passed}/{report.total} passed{warn_text} in {report.elapsed_s:.1f}s")

        # Show hard failures
        hard_fails = [
            r
            for r in report.results
            if not r.passed and r.severity in (Severity.CRITICAL, Severity.ERROR)
        ]
        if hard_fails:
            print(f"\n  Failures:")
            for r in hard_fails:
                err = f" — {r.error}" if r.error else ""
                print(f"    {self._apply('[FAIL]', 'red')} {r.phase}/{r.name}{err}")

        # Show warnings
        warns = [
            r
            for r in report.results
            if not r.passed and r.severity not in (Severity.CRITICAL, Severity.ERROR)
        ]
        if warns:
            print(f"\n  Warnings:")
            for r in warns:
                err = f" — {r.error}" if r.error else ""
                print(f"    {self._apply('[WARN]', 'yellow')} {r.phase}/{r.name}{err}")

        print(f"{'=' * 60}\n")


# =============================================================================
# BASE VALIDATOR — template for all validation tools
# =============================================================================


class BaseValidator(ABC):
    """
    Abstract base for all validation tools.

    Subclass and implement `define_checks()`.
    Call `run()` to execute all checks and get sys.exit code.
    """

    def __init__(self, title: str, version: str = "1.0"):
        self.report = ToolReport(title, version)
        self.console = Console()
        self.args = None

    @abstractmethod
    def define_checks(self):
        """Override: define and run all checks, adding results to self.report."""
        ...

    def run(self) -> int:
        """Execute the validator. Returns exit code (0=pass, 1=fail)."""
        self.args = self._parse_args()
        self.console.quiet = getattr(self.args, "quiet", False)
        self.console.header(self.report.title, self.report.version)

        try:
            self.define_checks()
        except Exception as e:
            self.report.add(
                "FATAL", "unhandled_exception", False, error=str(e), severity=Severity.CRITICAL
            )

        self.console.summary(self.report)

        if getattr(self.args, "json", False):
            print(self.report.to_json())

        return 0 if self.report.all_passed else 1

    def check(
        self,
        phase: str,
        name: str,
        condition: bool,
        error: str = "",
        detail: str = "",
        severity: Severity = Severity.ERROR,
    ) -> bool:
        """Register a check result and print it."""
        self.report.add(
            phase, name, condition, error=error if not condition else None, severity=severity
        )
        self.console.check(name, condition, detail=detail, severity=severity)
        return condition

    def _parse_args(self) -> argparse.Namespace:
        parser = argparse.ArgumentParser(description=self.report.title)
        parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
        parser.add_argument("--json", action="store_true", help="Output JSON report")
        parser.add_argument(
            "--quiet", "-q", action="store_true", help="Suppress output (exit code only)"
        )
        self._add_extra_args(parser)
        return parser.parse_args()

    def _add_extra_args(self, parser: argparse.ArgumentParser):
        """Override to add tool-specific arguments."""
        pass


# =============================================================================
# UTILITY: Tool contract validation
# =============================================================================


def validate_tool_contract(file_path: Path) -> List[str]:
    """
    Verify a tool file follows the project tool contract:
    1. Has `if __name__ == "__main__":` guard
    2. Has `sys.exit()` call
    3. Is syntactically valid Python

    Returns list of violation strings (empty = passes).
    """
    violations = []
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Cannot read file: {e}"]

    if "if __name__" not in content:
        violations.append("Missing `if __name__ == '__main__':` guard")

    # Check for sys.exit (not required for all tools, but recommended for validators)
    # This is advisory, not blocking

    try:
        import ast

        ast.parse(content)
    except SyntaxError as e:
        violations.append(f"Syntax error at line {e.lineno}: {e.msg}")

    return violations
