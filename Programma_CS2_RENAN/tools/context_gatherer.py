#!/usr/bin/env python3
"""Gather all relational context for a given file — imports, dependents, tests, API, git."""

import argparse
import ast
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from _infra import path_stabilize

PROJECT_ROOT, SOURCE_ROOT = path_stabilize()

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.context_gatherer")

VERSION = "1.0"
SEP = " \u25aa "

# Python stdlib module names (3.10+)
try:
    STDLIB = set(sys.stdlib_module_names)
except AttributeError:
    # Fallback for older Python
    STDLIB = {
        "abc",
        "argparse",
        "ast",
        "asyncio",
        "base64",
        "collections",
        "contextlib",
        "copy",
        "csv",
        "dataclasses",
        "datetime",
        "enum",
        "functools",
        "hashlib",
        "importlib",
        "inspect",
        "io",
        "itertools",
        "json",
        "logging",
        "math",
        "multiprocessing",
        "operator",
        "os",
        "pathlib",
        "pickle",
        "platform",
        "pprint",
        "queue",
        "random",
        "re",
        "shutil",
        "signal",
        "socket",
        "sqlite3",
        "statistics",
        "string",
        "struct",
        "subprocess",
        "sys",
        "tempfile",
        "textwrap",
        "threading",
        "time",
        "traceback",
        "typing",
        "unittest",
        "urllib",
        "uuid",
        "warnings",
        "weakref",
    }


# ─── Safe wrapper ─────────────────────────────────────────────────────────────


def _safe(fn, fallback=None):
    try:
        return fn()
    except Exception as e:
        logger.warning("%s failed: %s", fn.__name__, e)
        return fallback if fallback is not None else {"error": str(e)}


# ─── Target resolution ────────────────────────────────────────────────────────


def resolve_target(target: str) -> Path:
    """Resolve a file path or dotted module name to an absolute Path."""
    # 1. Absolute path
    p = Path(target)
    if p.is_absolute() and p.exists():
        return p

    # 2. Relative from PROJECT_ROOT
    candidate = PROJECT_ROOT / target
    if candidate.exists():
        return candidate

    # 3. Relative from SOURCE_ROOT
    candidate = SOURCE_ROOT / target
    if candidate.exists():
        return candidate

    # 4. Dotted module name → path
    dotted = target.replace(".", "/")
    for base in [PROJECT_ROOT, SOURCE_ROOT]:
        candidate = base / (dotted + ".py")
        if candidate.exists():
            return candidate
        # Try as package
        candidate = base / dotted / "__init__.py"
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"Cannot resolve target: {target}")


# ─── Collectors ───────────────────────────────────────────────────────────────


def collect_file_info(p: Path) -> dict:
    stat = p.stat()
    content = p.read_text(encoding="utf-8", errors="replace")
    loc = len(content.splitlines())
    size_kb = round(stat.st_size / 1024, 1)
    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")

    try:
        rel = p.relative_to(PROJECT_ROOT)
    except ValueError:
        rel = p
    return {
        "path": str(rel).replace("\\", "/"),
        "loc": loc,
        "size_kb": size_kb,
        "modified": modified,
    }


def collect_structure(p: Path) -> dict:
    source = p.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"SyntaxError at line {e.lineno}: {e.msg}"}

    classes = []
    functions = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods = [
                n.name
                for n in ast.iter_child_nodes(node)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            classes.append({"name": node.name, "methods": methods, "method_count": len(methods)})

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = []
            for a in node.args.args:
                args.append(a.arg)
            ret = None
            if node.returns:
                try:
                    ret = ast.unparse(node.returns)
                except Exception:
                    ret = "?"
            functions.append({"name": node.name, "args": args, "returns": ret})

    return {
        "classes": classes,
        "functions": functions,
        "class_count": len(classes),
        "function_count": len(functions),
    }


def _classify_import(module_name: str) -> str:
    if not module_name:
        return "std"
    top = module_name.split(".")[0]
    if top == "Programma_CS2_RENAN":
        return "proj"
    if top in STDLIB:
        return "std"
    return "ext"


def collect_imports(p: Path) -> dict:
    source = p.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {"error": "SyntaxError"}

    proj, std, ext = [], [], []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                cat = _classify_import(alias.name)
                target = {"proj": proj, "std": std, "ext": ext}[cat]
                if alias.name not in target:
                    target.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                cat = _classify_import(node.module)
                target = {"proj": proj, "std": std, "ext": ext}[cat]
                if node.module not in target:
                    target.append(node.module)

    return {"proj": sorted(proj), "std": sorted(std), "ext": sorted(ext)}


def collect_forward_deps(p: Path, imports: dict) -> list:
    """Resolve project imports to actual file paths."""
    deps = []
    proj_imports = imports.get("proj", [])

    for mod in proj_imports:
        dotted = mod.replace(".", "/")
        candidate = PROJECT_ROOT / (dotted + ".py")
        if candidate.exists():
            try:
                rel = candidate.relative_to(PROJECT_ROOT)
                deps.append(str(rel).replace("\\", "/"))
            except ValueError:
                deps.append(str(candidate))
            continue

        # Try __init__.py
        candidate = PROJECT_ROOT / dotted / "__init__.py"
        if candidate.exists():
            try:
                rel = candidate.relative_to(PROJECT_ROOT)
                deps.append(str(rel).replace("\\", "/"))
            except ValueError:
                deps.append(str(candidate))

    return deps


def collect_reverse_deps(p: Path) -> list:
    """Find all .py files that import this module."""
    try:
        rel = p.relative_to(PROJECT_ROOT)
    except ValueError:
        return []

    # Build search patterns
    rel_posix = str(rel).replace("\\", "/")
    # e.g. "Programma_CS2_RENAN/backend/analysis/role_classifier.py"
    module_dotted = rel_posix.replace("/", ".").replace(".py", "")
    # e.g. "Programma_CS2_RENAN.backend.analysis.role_classifier"

    # Also check without the top-level package for relative imports
    stem = rel_posix.replace(".py", "").split("/")[-1]
    # e.g. "role_classifier"

    patterns = [module_dotted]
    # Also match partial import paths (from backend.analysis.role_classifier import ...)
    parts = module_dotted.split(".")
    if len(parts) > 1:
        # Without top package
        patterns.append(".".join(parts[1:]))

    reverse = []
    for py_file in SOURCE_ROOT.rglob("*.py"):
        if py_file == p:
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # F8-11: Substring matching creates false reverse deps from comments/strings.
        # Use dead_code_detector.py for accurate AST-based import analysis.
        for pattern in patterns:
            if pattern in content:
                try:
                    r = py_file.relative_to(PROJECT_ROOT)
                    path_str = str(r).replace("\\", "/")
                    if path_str not in reverse:
                        reverse.append(path_str)
                except ValueError:
                    pass
                break

    return reverse


def collect_related_tests(p: Path) -> list:
    """Find test files that reference this module."""
    tests_dir = SOURCE_ROOT / "tests"
    if not tests_dir.exists():
        return []

    try:
        rel = p.relative_to(PROJECT_ROOT)
    except ValueError:
        return []

    stem = p.stem  # e.g. "role_classifier"
    rel_posix = str(rel).replace("\\", "/")
    module_dotted = rel_posix.replace("/", ".").replace(".py", "")

    related = []
    for test_file in tests_dir.rglob("test_*.py"):
        try:
            content = test_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # Check if test references this module by name or import
        if stem in content or module_dotted in content:
            try:
                r = test_file.relative_to(PROJECT_ROOT)
                related.append(str(r).replace("\\", "/"))
            except ValueError:
                pass

    return related


def collect_git_history(p: Path) -> list:
    try:
        rel = p.relative_to(PROJECT_ROOT)
    except ValueError:
        return []

    # F8-34: subprocess.run() uses list args (shell=False by default) with timeout=10.
    # Path comes from relative_to(PROJECT_ROOT) — no injection risk. Pattern is correct.
    result = subprocess.run(
        ["git", "log", "-5", "--format=%h %ad %s", "--date=short", "--", str(rel)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=10,
    )
    if result.returncode != 0:
        return []

    commits = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split(" ", 2)
        if len(parts) >= 3:
            msg = parts[2]
            if len(msg) > 50:
                msg = msg[:47] + "..."
            commits.append({"hash": parts[0], "date": parts[1], "msg": msg})
        elif len(parts) == 2:
            commits.append({"hash": parts[0], "date": parts[1], "msg": ""})

    return commits


def collect_public_api(p: Path) -> list:
    source = p.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    api = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            # Class signature
            bases = []
            for b in node.bases:
                try:
                    bases.append(ast.unparse(b))
                except Exception:
                    bases.append("?")
            base_str = f"({', '.join(bases)})" if bases else ""
            api.append(f"class {node.name}{base_str}")

            # Public methods
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not child.name.startswith("_"):
                        sig = _format_signature(child)
                        api.append(f"  {sig}")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                sig = _format_signature(node)
                api.append(f"fn {sig}")

    return api


def _format_signature(node) -> str:
    """Format a function/method AST node as a human-readable signature."""
    args = []
    for a in node.args.args:
        if a.arg == "self":
            continue
        annotation = ""
        if a.annotation:
            try:
                annotation = f": {ast.unparse(a.annotation)}"
            except Exception:
                annotation = ": ?"
        args.append(f"{a.arg}{annotation}")

    ret = ""
    if node.returns:
        try:
            ret = f" -> {ast.unparse(node.returns)}"
        except Exception:
            ret = " -> ?"

    return f"{node.name}({', '.join(args)}){ret}"


# ─── Formatting ───────────────────────────────────────────────────────────────


def format_compact(data):
    lines = []
    fi = data.get("file_info", {})
    name = fi.get("path", "?").split("/")[-1]
    lines.append(f"── context: {name} {'─' * max(1, 48 - len(name))}")
    lines.append("")

    # File info
    if "error" in fi:
        lines.append(f"file   {fi['error']}")
    else:
        lines.append(
            f"file   {fi['path']}{SEP}{fi['loc']}loc{SEP}{fi['size_kb']}KB{SEP}{fi['modified']}"
        )

    # Structure
    st = data.get("structure", {})
    if "error" in st:
        lines.append(f"struct {st['error']}")
    else:
        lines.append(
            f"struct {st.get('class_count', 0)} classes{SEP}{st.get('function_count', 0)} functions"
        )
        for cls in st.get("classes", []):
            methods = cls.get("methods", [])
            method_names = ", ".join(methods[:8])
            if len(methods) > 8:
                method_names += ", ..."
            lines.append(f"       {cls['name']}({cls['method_count']} methods): {method_names}")
        for fn in st.get("functions", []):
            args_str = ", ".join(fn.get("args", []))
            ret = f" -> {fn['returns']}" if fn.get("returns") else ""
            lines.append(f"       fn: {fn['name']}({args_str}){ret}")

    # Imports
    imp = data.get("imports", {})
    if "error" not in imp:
        lines.append("")
        lines.append("imports")
        proj = imp.get("proj", [])
        ext = imp.get("ext", [])
        std = imp.get("std", [])
        if proj:
            lines.append(f"  proj  {', '.join(proj)}")
        if ext:
            lines.append(f"  ext   {', '.join(ext)}")
        if std:
            lines.append(f"  std   {', '.join(std)}")

    # Forward deps
    fwd = data.get("forward_deps", [])
    if fwd:
        short = [p.split("/")[-1] for p in fwd]
        lines.append(f"\nfwd\u2192   {SEP.join(short)}")

    # Reverse deps
    rev = data.get("reverse_deps", [])
    if rev:
        short = [p.split("/")[-1] for p in rev]
        lines.append(f"\u2190rev   {SEP.join(short[:6])}")
        if len(rev) > 6:
            lines.append(f"       ... and {len(rev) - 6} more ({len(rev)} total)")

    # Tests
    tests = data.get("tests", [])
    if tests:
        short = [p.split("/")[-1] for p in tests]
        lines.append(f"\ntests  {SEP.join(short)}")
    else:
        lines.append("\ntests  none")

    # Git
    git = data.get("git", [])
    if git:
        lines.append("")
        lines.append("git")
        for c in git:
            lines.append(f"       {c['hash']} {c['date']} {c['msg']}")

    # Public API
    api = data.get("api", [])
    if api:
        lines.append("")
        lines.append("api")
        for line in api:
            lines.append(f"       {line}")

    elapsed = data.get("elapsed_s", 0)
    lines.append("")
    lines.append(f"── {elapsed:.1f}s elapsed ──")
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Gather relational context for a file")
    parser.add_argument("target", help="File path or dotted module name")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress header/footer")
    args = parser.parse_args()

    t0 = time.time()

    try:
        target_path = resolve_target(args.target)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1  # F8-25: signal failure to calling scripts

    file_info = _safe(lambda: collect_file_info(target_path), {"error": "cannot read file"})
    structure = _safe(lambda: collect_structure(target_path), {"error": "cannot parse"})
    imports = _safe(lambda: collect_imports(target_path), {})
    forward_deps = _safe(lambda: collect_forward_deps(target_path, imports), [])
    reverse_deps = _safe(lambda: collect_reverse_deps(target_path), [])
    tests = _safe(lambda: collect_related_tests(target_path), [])
    git = _safe(lambda: collect_git_history(target_path), [])
    api = _safe(lambda: collect_public_api(target_path), [])

    data = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "file_info": file_info,
        "structure": structure,
        "imports": imports,
        "forward_deps": forward_deps,
        "reverse_deps": reverse_deps,
        "tests": tests,
        "git": git,
        "api": api,
        "elapsed_s": round(time.time() - t0, 1),
    }

    if args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(format_compact(data))

    return 0


if __name__ == "__main__":
    sys.exit(main())
