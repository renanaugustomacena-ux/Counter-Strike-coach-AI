"""
Console boot sequence validator.

Boots the Unified Console, waits for stabilization, then validates the
status dict structure and values against the actual ``SystemState`` and
``ServiceStatus`` enums.  Exits 0 on success, 1 on failure.
"""

import os
import sys
import time
from pathlib import Path

# --- Venv Guard ---
if sys.prefix == sys.base_prefix and not os.environ.get("CI"):
    print("ERROR: Not in venv. Run: source ~/.venvs/cs2analyzer/bin/activate", file=sys.stderr)
    sys.exit(2)

# Add project root to sys.path — anchored to __file__, not CWD
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from Programma_CS2_RENAN.backend.control.console import ServiceStatus, SystemState, get_console

# Derive valid values from the actual enums — never hardcode.
_VALID_STATES = {s.value for s in SystemState}
_VALID_SVC_STATUSES = {s.value for s in ServiceStatus}

# Required top-level keys in the status dict (from get_system_status()).
_REQUIRED_STATUS_KEYS = {
    "timestamp",
    "state",
    "services",
    "teacher",
    "ml_controller",
    "ingestion",
    "storage",
    "baseline",
    "training_data",
}

errors: list[str] = []


def _check(condition: bool, msg: str) -> None:
    if not condition:
        errors.append(msg)
        print(f"  [FAIL] {msg}")
    else:
        print(f"  [PASS] {msg}")


def main():
    print("=" * 60)
    print("      MACENA UNIFIED CONSOLE - BOOT SEQUENCE VALIDATOR")
    print("=" * 60)

    console = get_console()

    try:
        # --- Boot ---
        print("\n[*] Initiating System Boot...")
        console.boot()

        print("[*] Waiting for subsystems to stabilize (5s)...")
        time.sleep(5)

        # --- Fetch status ---
        print("\n--- SYSTEM STATUS ---")
        status = console.get_system_status()

        # --- Validate status dict structure ---
        print("\n[Phase 1] Status dict structure")
        _check(isinstance(status, dict), "get_system_status() returns a dict")

        missing_keys = _REQUIRED_STATUS_KEYS - set(status.keys())
        _check(
            not missing_keys,
            f"all required keys present (missing: {sorted(missing_keys) if missing_keys else 'none'})",
        )

        # --- Validate state value ---
        print("\n[Phase 2] State value")
        state_val = status.get("state")
        _check(
            state_val in _VALID_STATES,
            f"state='{state_val}' is a valid SystemState (valid: {sorted(_VALID_STATES)})",
        )

        # --- Validate timestamp ---
        _check(
            isinstance(status.get("timestamp"), str) and len(status["timestamp"]) > 10,
            f"timestamp is a non-empty ISO string: {status.get('timestamp', '???')[:25]}",
        )

        # --- Validate services ---
        print("\n[Phase 3] Services")
        services = status.get("services", {})
        if isinstance(services, dict) and "error" not in services:
            for name, svc in services.items():
                if isinstance(svc, dict):
                    svc_status = svc.get("status")
                    svc_pid = svc.get("pid")
                    _check(
                        svc_status in _VALID_SVC_STATUSES,
                        f"service '{name}' status='{svc_status}' is valid ServiceStatus",
                    )
                    _check(
                        svc_pid is None or isinstance(svc_pid, int),
                        f"service '{name}' PID type is int or None (got {type(svc_pid).__name__})",
                    )
                    print(f"      {name:<12}: {svc_status} (PID: {svc_pid})")
        else:
            print(f"  [INFO] Services returned error or non-dict: {services}")

        # --- Validate storage ---
        print("\n[Phase 4] Storage")
        storage = status.get("storage", {})
        if isinstance(storage, dict) and "error" not in storage:
            t12 = storage.get("tier1_2_size", 0)
            t3 = storage.get("tier3_count", 0)
            _check(isinstance(t12, (int, float)), f"tier1_2_size is numeric: {t12}")
            _check(isinstance(t3, int), f"tier3_count is int: {t3}")
            print(f"      Tier 1/2 Size: {t12 / (1024 * 1024):.2f} MB")
            print(f"      Tier 3 Count:  {t3} matches")
        else:
            print(f"  [INFO] Storage returned error: {storage}")

        # --- Validate baseline ---
        print("\n[Phase 5] Baseline")
        baseline = status.get("baseline", {})
        if isinstance(baseline, dict):
            _check(
                "stat_cards" in baseline, f"baseline has 'stat_cards': {baseline.get('stat_cards')}"
            )
            _check(
                baseline.get("mode") in ("temporal", "legacy", "unavailable"),
                f"baseline mode='{baseline.get('mode')}' is valid",
            )

    except Exception as e:
        errors.append(f"Boot sequence exception: {e}")
        print(f"\n[!] Boot failed: {e}")
    finally:
        print("\n[*] Shutting down gracefully...")
        try:
            console.shutdown()
        except Exception as e:
            print(f"[!] Shutdown error: {e}")

    # --- Summary ---
    print("\n" + "=" * 60)
    if errors:
        print(f"VERDICT: FAIL — {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("VERDICT: PASS — Console boot sequence validated")
    print("=" * 60)


if __name__ == "__main__":
    main()
