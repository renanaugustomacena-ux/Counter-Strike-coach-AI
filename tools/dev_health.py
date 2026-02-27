import argparse
import subprocess
import sys
import time
from pathlib import Path

# --- Configuration ---
script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent

# --- Tools to Run ---
# (Path relative to project root, Description, Critical?)
CHECKS = {
    "headless": ("tools/headless_validator.py", "Headless Validator (Backend + DB + ML)", True),
    "dead_code": (
        "tools/dead_code_detector.py",
        "Dead Code & Orphan Detector",
        False,
    ),  # Non-critical for now
    "feature": ("tools/Feature_Audit.py", "Feature Alignment Audit", False),
    "portability": ("tools/portability_test.py", "Cross-Platform Portability", False),
}


def run_check(key, fast_fail=True):
    path, desc, critical = CHECKS[key]
    print(f"\n[RUN] {desc}...")
    start = time.perf_counter()

    try:
        # flush output to keep order
        sys.stdout.flush()
        result = subprocess.run(
            [sys.executable, path], cwd=project_root, check=False  # We handle return code manually
        )
        elapsed = time.perf_counter() - start

        if result.returncode == 0:
            print(f"[PASS] {desc} ({elapsed:.1f}s)")
            return True
        else:
            print(f"[FAIL] {desc} (Exit: {result.returncode})")
            if critical and fast_fail:
                print("Critical check failed. Aborting.")
                sys.exit(1)
            return False

    except FileNotFoundError:
        print(f"[ERR] Tool not found: {path}")
        if critical:
            sys.exit(1)
        return False
    except Exception as e:
        print(f"[ERR] Failed to run {path}: {e}")
        if critical:
            sys.exit(1)
        return False


def main():
    parser = argparse.ArgumentParser(description="Macena Development Health Orchestrator")
    parser.add_argument(
        "--quick", action="store_true", help="Run only fast critical checks (Headless Validator)"
    )
    parser.add_argument("--full", action="store_true", help="Run ALL checks (Slow)")
    args = parser.parse_args()

    print("=" * 60)
    print("DEVELOPMENT HEALTH CHECK")
    print("=" * 60)

    # Always run headless validator
    success = run_check("headless")

    if args.quick:
        if success:
            print("\n[QUICK PASS] Critical systems healthy.")
            sys.exit(0)
        else:
            sys.exit(1)

    # Default (or Full) runs more
    all_passed = success

    if not run_check("dead_code", fast_fail=False):
        all_passed = False
    if not run_check("feature", fast_fail=False):
        all_passed = False

    if args.full:
        if not run_check("portability", fast_fail=False):
            all_passed = False

    print("\n[DONE] Health check complete.")
    if all_passed:
        print("[ALL PASS] All checks passed.")
    else:
        print("[WARN] Some checks failed. Review output above.")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
