#!/usr/bin/env python3
"""Policy-as-Code runner for Macena CS2 Analyzer.

Discovers all `SECURITY/policies/*.yaml` files (except `README.md`), evaluates each rule against
the repository, applies inline waivers and the SECURITY/waivers.yaml registry, and reports
violations. Exit code: 0 (warn-mode) or 1 (`--strict` with unwaived violations).

Usage:
    python tools/policy_runner.py                # warn-mode, all rules
    python tools/policy_runner.py --strict       # block on unwaived violations
    python tools/policy_runner.py --rule POL-CODE-01     # single rule
    python tools/policy_runner.py --json         # machine-readable output

Doctrine: §54 — Policy as Code Law. Every rule is executable. Waivers are time-bound.

Implementation notes:
- Stdlib + PyYAML only (no libcst yet — Phase 2 upgrade flagged in POL-DB-01).
- AST-required rules (POL-DB-01) currently use a regex heuristic and are warn-only.
- Waiver schema validated at load time; expired waivers fail the gate.

Exit codes:
    0 — all clear (or warn-mode with violations only)
    1 — strict mode and at least one unwaived violation
    2 — usage error / malformed policy or waiver file
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import fnmatch
import json
import pathlib
import re
import sys
from typing import Any, Iterable, Iterator

try:
    import yaml  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover
    sys.stderr.write(
        "policy_runner.py: PyYAML is required (pip install pyyaml).\n"
        f"  underlying error: {exc}\n"
    )
    sys.exit(2)


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
POLICIES_DIR = REPO_ROOT / "SECURITY" / "policies"
WAIVERS_FILE = REPO_ROOT / "SECURITY" / "waivers.yaml"

# Files that match these globs are NEVER scanned, regardless of policy `applies_to`.
# This is a defense in depth so a misconfigured policy can't accidentally walk huge trees.
HARD_EXCLUDES = (
    ".git/**",
    ".venv/**",
    "venv/**",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
    "node_modules/**",
    "dist/**",
    "build/**",
    "*.egg-info/**",
    ".idea/**",
    ".vscode/**",
)


# ──────────────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True)
class Violation:
    """A single rule violation."""

    rule_id: str
    severity: str  # "error" | "warn" | "info"
    file: str  # repo-relative path
    line: int  # 1-based; 0 if file-level
    message: str
    snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def render(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else self.file
        sev = {"error": "ERROR", "warn": "WARN ", "info": "INFO "}.get(
            self.severity, self.severity.upper()
        )
        out = f"  [{sev}] {self.rule_id}  {loc}  — {self.message.strip()}"
        if self.snippet:
            out += f"\n         {self.snippet.rstrip()[:160]}"
        return out


@dataclasses.dataclass
class Waiver:
    rule: str
    path: str
    match: str | None
    risk: str
    expires: dt.date
    owner: str
    justification: str

    def is_expired(self, today: dt.date | None = None) -> bool:
        today = today or dt.date.today()
        return self.expires < today

    def matches(self, violation: Violation) -> bool:
        if self.rule != violation.rule_id:
            return False
        # Path glob
        if not fnmatch.fnmatch(violation.file, self.path):
            return False
        # If the waiver has a `match`, it must appear in the snippet
        if self.match and self.match not in violation.snippet:
            return False
        return True


# ──────────────────────────────────────────────────────────────────────────────
# Loading
# ──────────────────────────────────────────────────────────────────────────────


def load_policies(policies_dir: pathlib.Path) -> list[dict[str, Any]]:
    """Load every *.yaml in policies_dir, skipping README.md."""
    if not policies_dir.is_dir():
        raise FileNotFoundError(f"Policies directory not found: {policies_dir}")
    out: list[dict[str, Any]] = []
    for p in sorted(policies_dir.iterdir()):
        if p.name.lower() == "readme.md":
            continue
        if p.suffix.lower() not in (".yaml", ".yml"):
            continue
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise SystemExit(f"Malformed policy YAML in {p}: {exc}") from exc
        if not isinstance(data, dict):
            raise SystemExit(f"Policy {p} must be a top-level mapping")
        for required in ("id", "description", "severity", "applies_to", "kind"):
            if required not in data:
                raise SystemExit(f"Policy {p} missing required key: {required}")
        out.append(data)
    return out


def load_waivers(waivers_file: pathlib.Path) -> list[Waiver]:
    if not waivers_file.is_file():
        return []
    try:
        data = yaml.safe_load(waivers_file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise SystemExit(f"Malformed waivers file {waivers_file}: {exc}") from exc
    items = data.get("waivers") or []
    out: list[Waiver] = []
    for i, w in enumerate(items):
        if not isinstance(w, dict):
            raise SystemExit(f"Waiver #{i} must be a mapping")
        try:
            expires = w["expires"]
            if isinstance(expires, str):
                expires = dt.date.fromisoformat(expires)
            elif isinstance(expires, dt.datetime):
                expires = expires.date()
            elif not isinstance(expires, dt.date):
                raise ValueError(f"expires must be a date, got {type(expires).__name__}")
            out.append(
                Waiver(
                    rule=str(w["rule"]),
                    path=str(w["path"]),
                    match=str(w["match"]) if w.get("match") is not None else None,
                    risk=str(w["risk"]).upper(),
                    expires=expires,
                    owner=str(w["owner"]),
                    justification=str(w["justification"]),
                )
            )
        except KeyError as exc:
            raise SystemExit(f"Waiver #{i} missing required key {exc}") from exc
    return out


# ──────────────────────────────────────────────────────────────────────────────
# File walking
# ──────────────────────────────────────────────────────────────────────────────


def _matches_any_glob(path: str, patterns: Iterable[str]) -> bool:
    for p in patterns:
        # fnmatch handles single * and ?; we need ** semantics for nested dirs.
        # Approach: collapse `**/` into `*/` repeatedly via translate is heavy; instead use
        # a simple wildcard expansion that also matches multi-segment paths.
        if _glob_match(path, p):
            return True
    return False


def _glob_match(path: str, pattern: str) -> bool:
    """Glob match supporting `**` for any depth.

    Strategy: convert the pattern to a regex by translating `**` into `.*`, `*` into `[^/]*`,
    `?` into `[^/]`. Anchored at start and end.
    """
    if not pattern:
        return False
    # Quick path
    if pattern == "*" or pattern == "**":
        return True
    parts: list[str] = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                # `**`
                parts.append(".*")
                i += 2
                # Eat trailing slash if `**/` so it matches zero-or-more segments.
                if i < len(pattern) and pattern[i] == "/":
                    i += 1
            else:
                parts.append("[^/]*")
                i += 1
        elif c == "?":
            parts.append("[^/]")
            i += 1
        elif c in ".^$+(){}[]|\\":
            parts.append(re.escape(c))
            i += 1
        else:
            parts.append(c)
            i += 1
    regex = "^" + "".join(parts) + "$"
    return bool(re.match(regex, path))


def _iter_files(
    repo_root: pathlib.Path,
    applies_to: Iterable[str],
    excludes: Iterable[str],
) -> Iterator[pathlib.Path]:
    """Yield repo-relative file paths matching `applies_to` minus excludes/HARD_EXCLUDES."""
    excludes_combined = list(excludes) + list(HARD_EXCLUDES)

    # Walk the tree once; check inclusion lazily.
    for root, dirs, files in _safe_walk(repo_root):
        # Prune deeply excluded dirs in-place (saves time on .git/, .venv/, etc.)
        rel_root = root.relative_to(repo_root).as_posix()
        # Filter dirs first (in-place)
        kept_dirs = []
        for d in dirs:
            child = (
                pathlib.PurePosixPath(rel_root) / d if rel_root != "." else pathlib.PurePosixPath(d)
            ).as_posix()
            if any(_glob_match(child, ex.rstrip("/**").rstrip("/*")) for ex in HARD_EXCLUDES):
                continue
            kept_dirs.append(d)
        dirs[:] = kept_dirs

        for fn in files:
            child = (
                pathlib.PurePosixPath(rel_root) / fn
                if rel_root != "."
                else pathlib.PurePosixPath(fn)
            ).as_posix()
            if _matches_any_glob(child, excludes_combined):
                continue
            if _matches_any_glob(child, applies_to):
                yield repo_root / child


def _safe_walk(root: pathlib.Path) -> Iterator[tuple[pathlib.Path, list[str], list[str]]]:
    """os.walk yielding pathlib.Path and silently skipping unreadable dirs."""
    import os

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        yield pathlib.Path(dirpath), dirnames, filenames


# ──────────────────────────────────────────────────────────────────────────────
# Rule evaluators
# ──────────────────────────────────────────────────────────────────────────────


def _eval_line_regex(policy: dict[str, Any], file_path: pathlib.Path) -> Iterator[Violation]:
    config = policy.get("config", {})
    raw_patterns = config.get("patterns", [])
    inline_waivers: list[str] = config.get("inline_waivers", [])

    compiled: list[tuple[str, re.Pattern[str], str]] = []
    for entry in raw_patterns:
        sub_id = entry.get("id", "default")
        try:
            compiled.append((sub_id, re.compile(entry["pattern"]), entry.get("message", "")))
        except re.error as exc:
            raise SystemExit(f"Bad regex in {policy['id']}/{sub_id}: {exc}") from exc

    rel = file_path.relative_to(REPO_ROOT).as_posix()
    try:
        text = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return  # skip binaries / unreadable files

    for lineno, line in enumerate(text.splitlines(), start=1):
        if any(w in line for w in inline_waivers):
            continue
        for sub_id, regex, message in compiled:
            if regex.search(line):
                yield Violation(
                    rule_id=policy["id"],
                    severity=policy.get("severity", "error"),
                    file=rel,
                    line=lineno,
                    message=message or f"Sub-rule {sub_id} matched",
                    snippet=line.strip(),
                )


def _eval_text_regex(policy: dict[str, Any], file_path: pathlib.Path) -> Iterator[Violation]:
    config = policy.get("config", {})
    raw_patterns = config.get("patterns", [])
    inline_waivers: list[str] = config.get("inline_waivers", [])

    rel = file_path.relative_to(REPO_ROOT).as_posix()
    try:
        text = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return

    for entry in raw_patterns:
        sub_id = entry.get("id", "default")
        try:
            regex = re.compile(entry["pattern"], re.MULTILINE | re.DOTALL)
        except re.error as exc:
            raise SystemExit(f"Bad regex in {policy['id']}/{sub_id}: {exc}") from exc
        for m in regex.finditer(text):
            line = text[: m.start()].count("\n") + 1
            line_text = text.splitlines()[line - 1] if line - 1 < len(text.splitlines()) else ""
            if any(w in line_text for w in inline_waivers):
                continue
            yield Violation(
                rule_id=policy["id"],
                severity=policy.get("severity", "error"),
                file=rel,
                line=line,
                message=entry.get("message", f"Sub-rule {sub_id} matched"),
                snippet=line_text.strip(),
            )


def _eval_yaml_walker(policy: dict[str, Any], file_path: pathlib.Path) -> Iterator[Violation]:
    config = policy.get("config", {})
    rule = config.get("rule", "")
    rel = file_path.relative_to(REPO_ROOT).as_posix()
    try:
        data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        yield Violation(
            rule_id=policy["id"],
            severity="warn",
            file=rel,
            line=0,
            message=f"YAML parse error: {exc}",
        )
        return
    if data is None:
        return

    if rule == "must_exist_at_top_level":
        query = config.get("query", "")
        if not isinstance(data, dict) or query not in data:
            yield Violation(
                rule_id=policy["id"],
                severity=policy.get("severity", "warn"),
                file=rel,
                line=0,
                message=config.get(
                    "message",
                    f"Top-level key `{query}` is missing.",
                ),
            )
        return

    if rule == "must_not_match":
        # Walk the YAML, find values matching `query` (a simplified JSONPath subset),
        # then assert each value does not match `pattern`.
        # Phase 1: implement a minimal subset — `.services.*.ports[*]` style.
        query = config.get("query", "")
        pattern = re.compile(config.get("pattern", ""))
        message = config.get("message", "Value matched forbidden pattern.")
        for path_str, value in _yaml_walk(data, query):
            if isinstance(value, str) and pattern.search(value):
                yield Violation(
                    rule_id=policy["id"],
                    severity=policy.get("severity", "warn"),
                    file=rel,
                    line=0,
                    message=f"{message} ({path_str}={value})",
                    snippet=value,
                )


def _yaml_walk(data: Any, query: str, prefix: str = "") -> Iterator[tuple[str, Any]]:
    """Minimal JSONPath-style walker. Supports `.key`, `.*` (any key), `[*]` (any index)."""
    if not query:
        return
    parts = [p for p in query.replace("[*]", ".[*]").split(".") if p]

    def walk(node: Any, idx: int, path_str: str) -> Iterator[tuple[str, Any]]:
        if idx == len(parts):
            yield path_str, node
            return
        seg = parts[idx]
        if seg == "*":
            if isinstance(node, dict):
                for k, v in node.items():
                    yield from walk(v, idx + 1, f"{path_str}.{k}")
        elif seg == "[*]":
            if isinstance(node, list):
                for i, v in enumerate(node):
                    yield from walk(v, idx + 1, f"{path_str}[{i}]")
        else:
            if isinstance(node, dict) and seg in node:
                yield from walk(node[seg], idx + 1, f"{path_str}.{seg}")

    yield from walk(data, 0, prefix)


def _eval_file_compare(policy: dict[str, Any]) -> Iterator[Violation]:
    """Compare a regex-extract from one file with another."""
    config = policy.get("config", {})
    left_cfg = config.get("left", {})
    right_cfg = config.get("right", {})
    rule = config.get("rule", "must_be_equal")

    left_val = _extract_value(REPO_ROOT / left_cfg["path"], left_cfg["extract"])
    right_val = _extract_value(REPO_ROOT / right_cfg["path"], right_cfg["extract"])

    if left_val is None:
        yield Violation(
            rule_id=policy["id"],
            severity="warn",
            file=left_cfg["path"],
            line=0,
            message=f"Could not extract value matching {left_cfg['extract']!r}",
        )
        return
    if right_val is None:
        yield Violation(
            rule_id=policy["id"],
            severity="warn",
            file=right_cfg["path"],
            line=0,
            message=f"Could not extract value matching {right_cfg['extract']!r}",
        )
        return

    if rule == "must_be_equal" and left_val != right_val:
        msg_template = config.get("message", "Value mismatch: {left} != {right}")
        message = msg_template.format(left=left_val, right=right_val)
        yield Violation(
            rule_id=policy["id"],
            severity=policy.get("severity", "error"),
            file=f"{left_cfg['path']} vs {right_cfg['path']}",
            line=0,
            message=message,
        )


def _extract_value(path: pathlib.Path, regex_pattern: str) -> str | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(regex_pattern, text)
    if not m:
        return None
    return m.group(1) if m.groups() else m.group(0)


def _eval_ast_walker(policy: dict[str, Any], _file_path: pathlib.Path) -> Iterator[Violation]:
    # Phase 2: requires libcst. Until then, this is a no-op + warning.
    yield Violation(
        rule_id=policy["id"],
        severity="info",
        file="(meta)",
        line=0,
        message="AST walker not yet implemented (Phase 2 with libcst dep).",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Engine
# ──────────────────────────────────────────────────────────────────────────────


def evaluate_policy(policy: dict[str, Any]) -> list[Violation]:
    kind = policy["kind"]
    violations: list[Violation] = []

    if kind == "file_compare":
        violations.extend(_eval_file_compare(policy))
        return violations

    if kind == "ast_walker":
        violations.extend(_eval_ast_walker(policy, REPO_ROOT))
        return violations

    applies_to = policy.get("applies_to", [])
    excludes = policy.get("excludes", []) or []

    for f in _iter_files(REPO_ROOT, applies_to, excludes):
        if kind == "line_regex":
            violations.extend(_eval_line_regex(policy, f))
        elif kind == "text_regex":
            violations.extend(_eval_text_regex(policy, f))
        elif kind == "yaml_walker":
            violations.extend(_eval_yaml_walker(policy, f))
        else:
            violations.append(
                Violation(
                    rule_id=policy["id"],
                    severity="warn",
                    file=f.relative_to(REPO_ROOT).as_posix(),
                    line=0,
                    message=f"Unknown policy kind: {kind!r}",
                )
            )
    return violations


def filter_waived(
    violations: list[Violation],
    waivers: list[Waiver],
    today: dt.date | None = None,
) -> tuple[list[Violation], list[Violation], list[Waiver]]:
    """Return (unwaived, waived, expired_waivers)."""
    today = today or dt.date.today()
    expired = [w for w in waivers if w.is_expired(today)]
    active = [w for w in waivers if not w.is_expired(today)]
    unwaived: list[Violation] = []
    waived: list[Violation] = []
    for v in violations:
        if any(w.matches(v) for w in active):
            waived.append(v)
        else:
            unwaived.append(v)
    return unwaived, waived, expired


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run policy-as-code rules against the repository.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on any unwaived violation. Default is warn-mode (exit 0).",
    )
    parser.add_argument(
        "--rule",
        action="append",
        default=[],
        help="Run only the specified rule ID(s). Can be repeated.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human report.",
    )
    parser.add_argument(
        "--policies-dir",
        type=pathlib.Path,
        default=POLICIES_DIR,
        help=f"Override policies directory (default: {POLICIES_DIR}).",
    )
    parser.add_argument(
        "--waivers-file",
        type=pathlib.Path,
        default=WAIVERS_FILE,
        help=f"Override waivers file (default: {WAIVERS_FILE}).",
    )
    args = parser.parse_args(argv)

    try:
        policies = load_policies(args.policies_dir)
    except FileNotFoundError as exc:
        sys.stderr.write(f"policy_runner: {exc}\n")
        return 2
    if args.rule:
        wanted = set(args.rule)
        policies = [p for p in policies if p["id"] in wanted]
        missing = wanted - {p["id"] for p in policies}
        if missing:
            sys.stderr.write(f"policy_runner: unknown rule(s): {sorted(missing)}\n")
            return 2

    waivers = load_waivers(args.waivers_file)

    all_violations: list[Violation] = []
    by_rule: dict[str, list[Violation]] = {}
    for policy in policies:
        v = evaluate_policy(policy)
        all_violations.extend(v)
        by_rule[policy["id"]] = v

    unwaived, waived, expired = filter_waived(all_violations, waivers)

    # ── Output ──
    if args.json:
        payload: dict[str, Any] = {
            "policies_evaluated": [p["id"] for p in policies],
            "violations_total": len(all_violations),
            "violations_unwaived": len(unwaived),
            "violations_waived": len(waived),
            "expired_waivers": [dataclasses.asdict(w) for w in expired],
            "by_rule": {rule: [v.to_dict() for v in vs] for rule, vs in by_rule.items() if vs},
            "unwaived": [v.to_dict() for v in unwaived],
        }
        json.dump(payload, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        out = sys.stdout
        out.write("=" * 72 + "\n")
        out.write("Policy-as-Code Runner — SECURITY/policies/\n")
        out.write("=" * 72 + "\n")
        out.write(f"Policies evaluated: {len(policies)}\n")
        out.write(f"Mode: {'STRICT (block)' if args.strict else 'warn-mode (informational)'}\n")
        out.write(
            f"Violations: {len(all_violations)} total | "
            f"{len(unwaived)} unwaived | {len(waived)} waived\n"
        )
        if expired:
            out.write(f"⚠ Expired waivers: {len(expired)}\n")
            for w in expired:
                out.write(f"    {w.rule}  {w.path}  expired={w.expires}  owner={w.owner}\n")
        out.write("\n")

        if unwaived:
            out.write("--- UNWAIVED ---\n")
            errors = sum(1 for v in unwaived if v.severity == "error")
            warns = sum(1 for v in unwaived if v.severity == "warn")
            infos = sum(1 for v in unwaived if v.severity == "info")
            out.write(f"  errors: {errors}  warns: {warns}  infos: {infos}\n\n")
            for v in unwaived:
                out.write(v.render() + "\n")
            out.write("\n")
        else:
            out.write("✓ No unwaived violations.\n")

        if waived:
            out.write(f"\n--- WAIVED ({len(waived)}) ---\n")
            for v in waived[:20]:
                out.write(v.render() + "\n")
            if len(waived) > 20:
                out.write(f"  ... and {len(waived) - 20} more\n")

        out.write("\n")

    # Strict mode fails on any unwaived ERROR-severity violation, OR on expired waivers.
    if args.strict:
        unwaived_errors = [v for v in unwaived if v.severity == "error"]
        if unwaived_errors or expired:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
