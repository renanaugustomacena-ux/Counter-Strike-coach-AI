import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from Programma_CS2_RENAN.backend.control.console import get_console


def main():
    print("=" * 60)
    print("      MACENA UNIFIED CONSOLE - BOOT SEQUENCE")
    print("=" * 60)

    console = get_console()

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

    print("\n[*] Boot Sequence Complete. Shutting down gracefully...")
    console.shutdown()
    print("=" * 60)


if __name__ == "__main__":
    main()
