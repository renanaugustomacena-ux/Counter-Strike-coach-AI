#!/usr/bin/env python3
"""
Mechanical codebase audit scanner.

Accepts a subsystem path and produces a structured report:
- Module inventory (files, LOC, public classes/functions)
- Import graph (internal cross-references)
- Test coverage map (which files have tests)
- Pattern violations (bare except, print(), logging.basicConfig, etc.)
- TODO/FIXME/HACK scan
- Cyclomatic complexity per function
- Missing docstrings on public API

Usage:
    python tools/audit_scanner.py Programma_CS2_RENAN/core
    python tools/audit_scanner.py Programma_CS2_RENAN/backend/storage --format markdown
    python tools/audit_scanner.py Programma_CS2_RENAN/backend/nn --output reports/audit/nn_scan.json
"""

import ast
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = PROJECT_ROOT / "Programma_CS2_RENAN"
TEST_DIRS = [
    PROJECT_ROOT / "Programma_CS2_RENAN" / "tests",
    PROJECT_ROOT / "tests",
]


# ── Module Inventory ──────────────────────────────────────────────────


def list_modules(subsystem_path: Path) -> list[dict]:
    """List all .py files in a directory with line counts."""
    modules = []
    for py_file in sorted(subsystem_path.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        rel = py_file.relative_to(PROJECT_ROOT)
        try:
            lines = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            lines = []
        modules.append(
            {
                "path": str(rel),
                "filename": py_file.name,
                "loc": len(lines),
                "abs_path": str(py_file),
            }
        )
    return modules


# ── AST-Based Analysis ────────────────────────────────────────────────


def extract_public_api(filepath: str) -> dict:
    """Extract classes, functions, and __all__ from a Python file using AST."""
    result = {
        "classes": [],
        "functions": [],
        "all_exports": None,
    }
    try:
        source = Path(filepath).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, UnicodeDecodeError):
        return result

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                has_docstring = (
                    isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, (ast.Constant,))
                    if node.body
                    else False
                )
                result["classes"].append(
                    {"name": node.name, "line": node.lineno, "has_docstring": has_docstring}
                )
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            if not node.name.startswith("_"):
                has_docstring = (
                    isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, (ast.Constant,))
                    if node.body
                    else False
                )
                result["functions"].append(
                    {"name": node.name, "line": node.lineno, "has_docstring": has_docstring}
                )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        result["all_exports"] = [
                            elt.value for elt in node.value.elts if isinstance(elt, (ast.Constant,))
                        ]
    return result


def map_imports(filepath: str) -> list[str]:
    """Extract all import targets from a Python file."""
    imports = []
    try:
        source = Path(filepath).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, UnicodeDecodeError):
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return sorted(set(imports))


def compute_complexity(filepath: str) -> list[dict]:
    """Compute cyclomatic complexity per function using AST branch counting."""
    results = []
    try:
        source = Path(filepath).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, UnicodeDecodeError):
        return results

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = 1  # Base complexity
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                    complexity += 1
                elif isinstance(child, ast.ExceptHandler):
                    complexity += 1
                elif (
                    isinstance(
                        child,
                        ast.With,
                    )
                    if hasattr(ast, "With")
                    else False
                ):
                    pass  # with doesn't add branches
                elif isinstance(child, ast.BoolOp):
                    complexity += len(child.values) - 1
                elif isinstance(child, ast.IfExp):
                    complexity += 1
            results.append(
                {
                    "function": node.name,
                    "line": node.lineno,
                    "complexity": complexity,
                }
            )
    return results


# ── Pattern Violation Scanner ─────────────────────────────────────────

PATTERN_CHECKS = [
    ("bare_except", re.compile(r"^\s*except\s*:", re.MULTILINE)),
    ("broad_except", re.compile(r"^\s*except\s+Exception\s*[:\s]", re.MULTILINE)),
    ("print_call", re.compile(r"(?<!\w)print\s*\(", re.MULTILINE)),
    ("logging_basicconfig", re.compile(r"logging\.basicConfig\s*\(", re.MULTILINE)),
    ("traceback_print", re.compile(r"traceback\.print_exc\s*\(", re.MULTILINE)),
    ("todo", re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b", re.MULTILINE | re.IGNORECASE)),
]


def scan_patterns(filepath: str) -> list[dict]:
    """Scan for pattern violations using regex."""
    violations = []
    try:
        lines = Path(filepath).read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return violations

    for line_num, line in enumerate(lines, 1):
        for name, pattern in PATTERN_CHECKS:
            if pattern.search(line):
                violations.append(
                    {
                        "type": name,
                        "line": line_num,
                        "text": line.strip()[:120],
                    }
                )
    return violations


# ── Test Coverage Map ─────────────────────────────────────────────────


def find_test_file(module_path: str) -> str | None:
    """Check if a corresponding test file exists for a module."""
    mod_name = Path(module_path).stem
    candidates = [
        f"test_{mod_name}.py",
        f"test_{mod_name}s.py",  # plural
    ]
    for test_dir in TEST_DIRS:
        if not test_dir.exists():
            continue
        for test_file in test_dir.rglob("test_*.py"):
            if test_file.name in candidates:
                return str(test_file.relative_to(PROJECT_ROOT))
        # Also check if module name appears in any test file name
        for test_file in test_dir.rglob("test_*.py"):
            if mod_name in test_file.stem:
                return str(test_file.relative_to(PROJECT_ROOT))
    return None


# ── Caller Map (who imports this module) ──────────────────────────────


def find_callers(module_rel_path: str) -> list[str]:
    """Find all .py files that import a given module (lightweight grep)."""
    callers = []
    mod_stem = Path(module_rel_path).stem
    if mod_stem == "__init__":
        return callers

    # Build possible import patterns
    parts = Path(module_rel_path).with_suffix("").parts
    # e.g., Programma_CS2_RENAN/core/config -> patterns like "core.config", "from Programma_CS2_RENAN.core.config"
    dotted = ".".join(parts)
    short_dotted = ".".join(parts[1:]) if len(parts) > 1 else dotted

    patterns = [mod_stem, dotted, short_dotted]

    for py_file in PACKAGE_ROOT.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        rel = str(py_file.relative_to(PROJECT_ROOT))
        if rel == module_rel_path:
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for pat in patterns:
            if pat in content:
                callers.append(rel)
                break

    return sorted(set(callers))


# ── Main Report Builder ───────────────────────────────────────────────


def audit_subsystem(subsystem_path: Path, find_callers_flag: bool = True) -> dict:
    """Run full audit on a subsystem directory."""
    modules = list_modules(subsystem_path)
    rel_subsystem = str(subsystem_path.relative_to(PROJECT_ROOT))

    report = {
        "subsystem": rel_subsystem,
        "scan_date": __import__("datetime").date.today().isoformat(),
        "summary": {},
        "files": [],
    }

    total_loc = 0
    total_violations = 0
    files_with_tests = 0
    high_complexity_functions = []
    all_todos = []

    for mod in modules:
        filepath = mod["abs_path"]
        rel_path = mod["path"]

        api = extract_public_api(filepath)
        imports = map_imports(filepath)
        violations = scan_patterns(filepath)
        complexity = compute_complexity(filepath)
        test_file = find_test_file(rel_path)
        callers = find_callers(rel_path) if find_callers_flag else []

        # Filter internal imports only
        internal_imports = [
            imp
            for imp in imports
            if imp.startswith("Programma_CS2_RENAN")
            or imp.startswith("core")
            or imp.startswith("backend")
        ]

        # Track high complexity
        for func in complexity:
            if func["complexity"] > 10:
                high_complexity_functions.append(
                    {
                        "file": rel_path,
                        "function": func["function"],
                        "line": func["line"],
                        "complexity": func["complexity"],
                    }
                )

        # Track TODOs
        for v in violations:
            if v["type"] == "todo":
                all_todos.append({"file": rel_path, "line": v["line"], "text": v["text"]})

        total_loc += mod["loc"]
        total_violations += len([v for v in violations if v["type"] != "todo"])
        if test_file:
            files_with_tests += 1

        # Missing docstrings on public API
        missing_docs = []
        for cls in api["classes"]:
            if not cls["has_docstring"]:
                missing_docs.append(f"class {cls['name']} (line {cls['line']})")
        for func in api["functions"]:
            if not func["has_docstring"]:
                missing_docs.append(f"def {func['name']} (line {func['line']})")

        file_entry = {
            "path": rel_path,
            "loc": mod["loc"],
            "classes": [c["name"] for c in api["classes"]],
            "functions": [f["name"] for f in api["functions"]],
            "imports_internal": internal_imports,
            "imported_by_count": len(callers),
            "imported_by": callers[:10],  # Cap at 10 for readability
            "has_test": test_file is not None,
            "test_file": test_file,
            "violations": violations,
            "violation_count": len([v for v in violations if v["type"] != "todo"]),
            "max_complexity": max((f["complexity"] for f in complexity), default=0),
            "missing_docstrings": missing_docs,
        }
        report["files"].append(file_entry)

    total_files = len(modules)
    report["summary"] = {
        "total_files": total_files,
        "total_loc": total_loc,
        "files_with_tests": files_with_tests,
        "files_without_tests": total_files - files_with_tests,
        "test_coverage_pct": round(files_with_tests / total_files * 100, 1) if total_files else 0,
        "total_violations": total_violations,
        "high_complexity_functions": len(high_complexity_functions),
        "todos": len(all_todos),
    }
    report["high_complexity"] = high_complexity_functions
    report["todos"] = all_todos

    return report


def format_markdown(report: dict) -> str:
    """Format the audit report as markdown."""
    lines = []
    s = report["summary"]
    sub = report["subsystem"]

    lines.append(f"# Audit Report: `{sub}`")
    lines.append(f"\n**Date:** {report['scan_date']}")
    lines.append(f"\n## Summary\n")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Files | {s['total_files']} |")
    lines.append(f"| Total LOC | {s['total_loc']} |")
    lines.append(f"| Files with tests | {s['files_with_tests']} ({s['test_coverage_pct']}%) |")
    lines.append(f"| Pattern violations | {s['total_violations']} |")
    lines.append(f"| High complexity functions (>10) | {s['high_complexity_functions']} |")
    lines.append(f"| TODO/FIXME/HACK markers | {s['todos']} |")

    lines.append(f"\n## Module Registry\n")
    lines.append("| File | LOC | Classes | Functions | Test | Violations | Max Complexity |")
    lines.append("|------|-----|---------|-----------|------|------------|----------------|")
    for f in report["files"]:
        classes = ", ".join(f["classes"][:3])
        if len(f["classes"]) > 3:
            classes += f" (+{len(f['classes'])-3})"
        funcs = ", ".join(f["functions"][:3])
        if len(f["functions"]) > 3:
            funcs += f" (+{len(f['functions'])-3})"
        test = "Yes" if f["has_test"] else "No"
        lines.append(
            f"| `{f['path']}` | {f['loc']} | {classes} | {funcs} | {test} | {f['violation_count']} | {f['max_complexity']} |"
        )

    if report["high_complexity"]:
        lines.append(f"\n## High Complexity Functions (>10)\n")
        lines.append("| File | Function | Line | Complexity |")
        lines.append("|------|----------|------|------------|")
        for hc in sorted(report["high_complexity"], key=lambda x: -x["complexity"]):
            lines.append(
                f"| `{hc['file']}` | `{hc['function']}` | {hc['line']} | {hc['complexity']} |"
            )

    if report["todos"]:
        lines.append(f"\n## TODO/FIXME/HACK Markers\n")
        lines.append("| File | Line | Text |")
        lines.append("|------|------|------|")
        for td in report["todos"]:
            text = td["text"].replace("|", "\\|")
            lines.append(f"| `{td['file']}` | {td['line']} | {text} |")

    # Pattern violations summary
    violation_types = defaultdict(int)
    for f in report["files"]:
        for v in f["violations"]:
            if v["type"] != "todo":
                violation_types[v["type"]] += 1
    if violation_types:
        lines.append(f"\n## Pattern Violations by Type\n")
        lines.append("| Type | Count |")
        lines.append("|------|-------|")
        for vtype, count in sorted(violation_types.items(), key=lambda x: -x[1]):
            lines.append(f"| {vtype} | {count} |")

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Audit scanner for CS2 Analyzer subsystems")
    parser.add_argument("subsystem", help="Path to subsystem directory (relative to project root)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--no-callers", action="store_true", help="Skip caller analysis (faster)")
    args = parser.parse_args()

    subsystem_path = PROJECT_ROOT / args.subsystem
    if not subsystem_path.is_dir():
        print(f"Error: {subsystem_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    report = audit_subsystem(subsystem_path, find_callers_flag=not args.no_callers)

    if args.format == "markdown":
        output = format_markdown(report)
    else:
        output = json.dumps(report, indent=2)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
