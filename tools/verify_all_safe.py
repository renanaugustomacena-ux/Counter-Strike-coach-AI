import os
import subprocess
import sys
import time
from pathlib import Path

# --- Venv Guard ---
if sys.prefix == sys.base_prefix and not os.environ.get("CI"):
    print("ERROR: Not in venv. Run: source ~/.venvs/cs2analyzer/bin/activate", file=sys.stderr)
    sys.exit(2)

# --- Path Stabilization ---
_script_dir = Path(__file__).parent.absolute()
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def run_tool(path_str, relative_name):
    print(f"\n[EXEC] Running {relative_name}...")
    start = time.time()

    # Special args for specific tools
    args = []
    if "build_pipeline.py" in relative_name:
        args = ["--test-only"]

    try:
        # We run as subprocess to ensure clean environment for each
        cmd = [sys.executable, path_str] + args
        res = subprocess.run(
            cmd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            cwd=_project_root,
            timeout=120,
        )

        duration = time.time() - start

        if res.returncode == 0:
            print(f" [PASS] {relative_name} ({duration:.2f}s)")
            return True, None
        else:
            print(f" [FAIL] {relative_name} (Exit Code: {res.returncode})")
            print("=" * 40)
            print(res.stderr[:1000])  # Cap output
            print("=" * 40)
            return False, res.stderr
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        print(f" [TIMEOUT] {relative_name} exceeded 120s limit ({duration:.2f}s)")
        return False, "Timed out after 120s"
    except Exception as e:
        print(f" [CRASH] {relative_name}: {e}")
        return False, str(e)


def is_safe_to_run(path_obj):
    name = path_obj.name.lower()

    # 1. Skip Deprecated
    if "deprecated" in name:
        return False

    # 2. Skip Destructive/Maintenance by convention.
    # F-0039: the original six prefixes missed 13 tools whose BARE
    # invocation mutates live data (audit census, docs/audit/FINDINGS.md)
    # — worst case rebuild_monolith, whose delete-first/bulk-insert-last
    # phase left pro stats EMPTY when the 120s timeout killed it mid-run.
    # The prefix families below cover every census member; tools that are
    # dry-run-by-default (rescrape_, sync_, merge_, seed_, d3_, d4_) stay
    # scheduled because their bare run is read-only by construction.
    unsafe_prefixes = [
        "fix_",
        "reset_",
        "migrate_",
        "patch_",
        "cleanup_",
        "force_",
        # F-0039 additions — bare invocation writes to live data:
        "repair_",
        "flag_",
        "purge_",
        "mine_",
        "populate_",
        "rebuild_",
        "observe_",
        "ingest_",
        "wipe_",
    ]
    if any(name.startswith(p) for p in unsafe_prefixes):
        return False

    # 3. Skip Interactive, Long Running, or Input-Requiring — each entry
    # names WHY (D-28: the sweep used to run these bare and report their
    # argparse usage errors as "SYSTEM UNSTABLE", drowning real failures).
    if name in _NAMED_SKIPS:
        return False

    return True


# D-28: tools whose bare run cannot succeed BY DESIGN — not instability.
# filename (lowercase) -> reason shown in the sweep report.
_NAMED_SKIPS = {
    "run_console_boot.py": "interactive console boot",
    # F-0039: Confirm-prompt blocks under a non-interactive runner
    # (the destructive path is only reachable via explicit --yes).
    "sanitize_project.py": "destructive; confirm-prompt blocks non-interactive run",
    # F-0039: default 30-minute fuzz budget guarantees a timeout-fail.
    "fuzz_demo_parser.py": "30-minute fuzz budget exceeds the 120s tool budget",
    "audit_scanner.py": "requires a subsystem argument",
    "build_web.py": "requires the Node/pnpm toolchain",
    "coach_answer_eval.py": "requires a running Ollama for the LLM eval",
    "drift_detector.py": "two-phase: needs a recorded --baseline first",
    "merge_demo_pool.py": "requires --source/--target demo pools",
    "seed_hltv_apply_vision.py": "data-entry tool; requires per-player args",
    "seed_hltv_top_n.py": "requires an explicit --dry-run/--apply and network",
    "test_tactical_pipeline.py": "requires a .dem file argument",
    "validate_coaching_pipeline.py": "requires a .dem file argument",
}


def verify_all_dynamic():
    print("=" * 80)
    print("      MACENA CS2 - DYNAMIC TOTAL SYSTEM VALIDATION")
    print("=" * 80)

    tools_dir = _project_root / "tools"
    all_tools = sorted(list(tools_dir.rglob("*.py")))

    safe_tools = []
    skipped = []

    for tool_path in all_tools:
        # Skip the verifier itself to avoid recursion loop if called weirdly
        if tool_path.name == "verify_all_safe.py":
            continue
        if is_safe_to_run(tool_path):
            safe_tools.append(tool_path)
        else:
            skipped.append(tool_path.name)

    print(f"Found {len(all_tools)} scripts.")
    print(f"Skipping {len(skipped)} scripts (unsafe-by-prefix or named):")
    for s in skipped:
        reason = _NAMED_SKIPS.get(s.lower(), "destructive/maintenance prefix (F-0039)")
        print(f"  - {s}: {reason}")
    print(f"Scheduled {len(safe_tools)} tools for execution.")
    print("-" * 80)

    passed_count = 0
    failures = []

    for tool_path in safe_tools:
        rel_path = tool_path.relative_to(_project_root)
        success, _ = run_tool(str(tool_path), str(rel_path))
        if success:
            passed_count += 1
        else:
            failures.append(str(rel_path))

    print("\n" + "=" * 80)
    print(" SUMMARY REPORT")
    print("=" * 80)
    print(f" Tools Executed: {passed_count}/{len(safe_tools)}")

    if len(failures) == 0:
        print(" result: [PASS] ALL SYSTEMS GREEN")
        sys.exit(0)
    else:
        print(" result: [FAIL] SYSTEM UNSTABLE")
        print(" Failed Tools:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    verify_all_dynamic()
