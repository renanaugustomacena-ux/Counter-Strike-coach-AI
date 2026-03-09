#!/usr/bin/env python3
"""
Build Tools — Consolidated build pipeline for Macena CS2 Analyzer.

Merges: build_pipeline, Build_Integrity_Verifier, Advanced_Build_Debugger

Usage:
  python build_tools.py build          Full build pipeline (lint, test, pyinstaller, hash)
  python build_tools.py verify         Post-build integrity verification
  python build_tools.py debug-build    Build with real-time error analysis
  python build_tools.py manifest       Generate/verify integrity manifest
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from _infra import PROJECT_ROOT, SOURCE_ROOT, Console, path_stabilize

path_stabilize()

console = Console()


def run_command(cmd, label, cwd=None, capture=False):
    """Execute a shell command with status reporting."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd or str(PROJECT_ROOT),
            capture_output=capture,
            text=True,
            timeout=600,
        )
        ok = result.returncode == 0
        detail = "success" if ok else f"exit code {result.returncode}"
        console.check(label, ok, detail=detail)
        return ok, result
    except subprocess.TimeoutExpired:
        console.check(label, False, detail="timeout (600s)")
        return False, None
    except Exception as e:
        console.check(label, False, detail=str(e))
        return False, None


def calculate_sha256(filepath):
    """Calculate SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# =============================================================================
# build — Full pipeline
# =============================================================================


def cmd_build(args):
    """Run the full deterministic build pipeline."""
    console.header("Build Pipeline", "3.0")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    console.section("Pre-Build Checks")
    ok, _ = run_command(
        "python -m black --check --line-length 100 Programma_CS2_RENAN/", "Black format check"
    )
    if not ok and not getattr(args, "force", False):
        print("  Run 'black Programma_CS2_RENAN/' to fix formatting.")

    ok, _ = run_command(
        "python -m isort --check --profile black --line-length 100 Programma_CS2_RENAN/",
        "isort import check",
    )

    console.section("Test Suite")
    ok, _ = run_command("python -m pytest Programma_CS2_RENAN/tests/ -x -q", "Pytest suite")
    if not ok:
        print("  ABORT: Tests must pass before build.")
        sys.exit(1)

    console.section("Database Migration")
    ok, _ = run_command("python -m alembic upgrade head", "Alembic migration")
    if not ok:
        print("  ABORT: Database migration must succeed before build.")
        sys.exit(1)

    console.section("PyInstaller Build")
    spec_file = SOURCE_ROOT / "macena.spec"
    if spec_file.exists():
        ok, _ = run_command(
            f"python -m PyInstaller --clean --noconfirm {spec_file}", "PyInstaller build"
        )
    else:
        console.check("PyInstaller build", False, detail="macena.spec not found")
        ok = False

    if ok:
        console.section("Integrity Hash")
        dist_dir = PROJECT_ROOT / "dist"
        if dist_dir.exists():
            # Collect platform-appropriate binary artifacts
            if sys.platform == "win32":
                binaries = list(dist_dir.rglob("*.exe"))
            else:
                # Linux/macOS: ELF/Mach-O binaries have no extension; find
                # executable files one level deep (PyInstaller dist/<name>/<name>)
                binaries = [
                    p for p in dist_dir.rglob("*")
                    if p.is_file() and os.access(str(p), os.X_OK) and "." not in p.name
                ]
            for exe in binaries:
                sha = calculate_sha256(exe)
                print(f"  {exe.name}: SHA256={sha[:16]}...")
                manifest = {
                    "file": exe.name,
                    "sha256": sha,
                    "built_at": datetime.now(timezone.utc).isoformat(),
                }
                (dist_dir / "build_manifest.json").write_text(json.dumps(manifest, indent=2))

    print("\nBuild pipeline complete.")


# =============================================================================
# verify — Post-build integrity
# =============================================================================


def cmd_verify(args):
    """Verify build artifacts for forbidden patterns and integrity."""
    console.header("Build Integrity Verifier", "3.0")

    dist_dir = PROJECT_ROOT / "dist"
    if not dist_dir.exists():
        print("  No dist/ directory found. Run 'build' first.")
        sys.exit(1)

    # Forbidden file patterns
    forbidden = [
        "*.db",
        "*.dem",
        "*.pt",
        "*.pth",
        "user_settings.json",
        "*.env",
        "*.pem",
        "*.key",
        "*.log",
    ]
    console.section("Forbidden Files Check")
    violations = []
    for pattern in forbidden:
        found = list(dist_dir.rglob(pattern))
        if found:
            violations.extend(found)
            console.check(f"No {pattern} in dist/", False, detail=f"{len(found)} found")
        else:
            console.check(f"No {pattern} in dist/", True)

    # Required files
    console.section("Required Files")
    required = ["macena.spec"]  # Add more as needed
    for req in required:
        p = SOURCE_ROOT / req
        console.check(f"{req} exists", p.exists())

    # SHA256 manifest
    console.section("Build Manifest")
    manifest = dist_dir / "build_manifest.json"
    if manifest.exists():
        data = json.loads(manifest.read_text())
        console.check(
            "Build manifest valid", "sha256" in data, detail=f"file={data.get('file', '?')}"
        )
    else:
        console.check("Build manifest", False, detail="not found (run build first)")

    # Report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "violations": [str(v) for v in violations],
        "passed": len(violations) == 0,
    }
    report_path = dist_dir / "build_integrity_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report: {report_path}")

    sys.exit(0 if len(violations) == 0 else 1)


# =============================================================================
# debug-build — Build with real-time error analysis
# =============================================================================

ERROR_PATTERNS = {
    r"ModuleNotFoundError: No module named '(\w+)'": "MISSING_MODULE",
    r"ImportError: cannot import name '(\w+)'": "IMPORT_ERROR",
    r"FileNotFoundError: \[Errno 2\]": "MISSING_FILE",
    r"SyntaxError": "SYNTAX_ERROR",
    r"PermissionError": "PERMISSION_ERROR",
    r"missing.*\.dll": "MISSING_DLL",
    r"UnicodeDecodeError": "ENCODING_ERROR",
}


def analyze_error(line):
    """Categorize a build error line."""
    for pattern, category in ERROR_PATTERNS.items():
        if re.search(pattern, line, re.IGNORECASE):
            return category
    return None


def cmd_debug_build(args):
    """Run build with real-time error analysis and categorization."""
    console.header("Build Debugger", "3.0")

    spec_file = SOURCE_ROOT / "macena.spec"
    if not spec_file.exists():
        print("  macena.spec not found.")
        sys.exit(1)

    cmd = f"python -m PyInstaller --clean --noconfirm {spec_file}"
    print(f"  Running: {cmd}")
    print(f"  Streaming output...\n")

    errors = []
    process = subprocess.Popen(
        cmd,
        shell=True,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    for line in process.stdout:
        line = line.rstrip()
        category = analyze_error(line)
        if category:
            errors.append({"line": line, "category": category})
            print(f"  [{category}] {line}")
        elif args.verbose if hasattr(args, "verbose") else False:
            print(f"  {line}")

    process.wait()

    # Summary
    print(f"\n{'='*60}")
    print(f"  Build {'SUCCEEDED' if process.returncode == 0 else 'FAILED'}")
    print(f"  Errors found: {len(errors)}")

    if errors:
        categories = {}
        for e in errors:
            categories[e["category"]] = categories.get(e["category"], 0) + 1
        for cat, count in sorted(categories.items()):
            print(f"    {cat}: {count}")

    # Save report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "exit_code": process.returncode,
        "errors": errors,
    }
    report_path = PROJECT_ROOT / "build_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report: {report_path}")

    sys.exit(process.returncode)


# =============================================================================
# manifest — Generate/verify integrity manifest
# =============================================================================


def cmd_manifest(args):
    """Generate or verify the project integrity manifest."""
    console.header("Integrity Manifest", "3.0")

    manifest_path = SOURCE_ROOT / "core" / "integrity_manifest.json"

    if getattr(args, "verify_only", False):
        if not manifest_path.exists():
            print("  Manifest not found.")
            sys.exit(1)
        data = json.loads(manifest_path.read_text())
        print(f"  Manifest loaded: {len(data.get('files', {}))} files")
        sys.exit(0)

    # Generate manifest
    print("  Generating integrity manifest...")
    try:
        result = subprocess.run(
            ["python", str(PROJECT_ROOT / "tools" / "generate_manifest.py")],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            print("  Manifest generated successfully.")
        else:
            print(f"  Error: {result.stderr}")
    except Exception as e:
        print(f"  Failed: {e}")
        sys.exit(1)


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Build Tools — Consolidated build pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Build operation")

    p_build = subparsers.add_parser("build", help="Full build pipeline")
    p_build.add_argument("--force", action="store_true", help="Continue on lint failures")

    subparsers.add_parser("verify", help="Post-build integrity verification")

    p_debug = subparsers.add_parser("debug-build", help="Build with error analysis")
    p_debug.add_argument("--verbose", "-v", action="store_true")

    p_manifest = subparsers.add_parser("manifest", help="Generate/verify integrity manifest")
    p_manifest.add_argument("--verify-only", action="store_true")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "build": cmd_build,
        "verify": cmd_verify,
        "debug-build": cmd_debug_build,
        "manifest": cmd_manifest,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
