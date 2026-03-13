import os
import sys
from pathlib import Path

# --- Import Guard: standalone diagnostic, not a pytest test ---
if __name__ != "__main__":
    raise ImportError(
        "check_failed_tasks.py is a standalone diagnostic. "
        "Run: python tests/forensics/check_failed_tasks.py"
    )

# --- Venv Guard ---
if sys.prefix == sys.base_prefix:
    print("ERROR: Not in venv.", file=sys.stderr)
    sys.exit(2)

# --- Path Stabilization ---
script_dir = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(os.path.dirname(script_dir))
if root not in sys.path:
    sys.path.insert(0, root)

from sqlmodel import select

from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import IngestionTask


def check_failed():
    db = get_db_manager()
    with db.get_session() as s:
        # TQ-F02-01: Limit query to prevent OOM on large failure backlogs
        tasks = s.exec(
            select(IngestionTask).where(IngestionTask.status == "failed").limit(500)
        ).all()
        print(f"Found {len(tasks)} failed tasks.")
        for t in tasks:
            print(f"Task {t.id} ({os.path.basename(t.demo_path)}): {t.error_message}")


if __name__ == "__main__":
    check_failed()
