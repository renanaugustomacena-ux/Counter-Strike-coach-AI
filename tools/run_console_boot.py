import sys
import time
from pathlib import Path

# --- Venv Guard ---
if sys.prefix == sys.base_prefix:
    print("ERROR: Not in venv. Run: source ~/.venvs/cs2analyzer/bin/activate", file=sys.stderr)
    sys.exit(2)

# Add project root to sys.path — anchored to __file__, not CWD
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from Programma_CS2_RENAN.backend.control.console import get_console


def main():
    print("=" * 60)
    print("      MACENA UNIFIED CONSOLE - BOOT SEQUENCE")
    print("=" * 60)

    console = get_console()

    try:
        print("[*] Initiating System Boot...")
        console.boot()

        print("\n[*] Waiting for subsystems to stabilize (5s)...")
        time.sleep(5)

        print("\n--- SYSTEM STATUS ---")
        status = console.get_system_status()

        print(f"Timestamp: {status['timestamp']}")
        print(f"State:     {status['state']}")

        print("\nServices:")
        for name, svc in status["services"].items():
            print(f"  - {name:<10}: {svc['status']} (PID: {svc['pid']})")

        print("\nStorage:")
        storage = status["storage"]
        print(f"  - Tier 1/2 Size: {storage.get('tier1_2_size', 0)/(1024*1024):.2f} MB")
        print(f"  - Tier 3 Count:  {storage.get('tier3_count', 0)} matches")

    except Exception as e:
        print(f"\n[!] Boot failed: {e}")
    finally:
        print("\n[*] Boot Sequence Complete. Shutting down gracefully...")
        try:
            console.shutdown()
        except Exception as e:
            print(f"[!] Shutdown error: {e}")
        print("=" * 60)


if __name__ == "__main__":
    main()
