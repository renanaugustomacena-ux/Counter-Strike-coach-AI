import os
import sys

from sqlalchemy import inspect

# --- Path Stabilization ---
script_dir = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(os.path.dirname(script_dir))
if root not in sys.path:
    sys.path.insert(0, root)

from Programma_CS2_RENAN.backend.storage.database import engine


def probe_tables():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Existing tables: {tables}")

    for table in tables:
        columns = [c["name"] for c in inspector.get_columns(table)]
        print(f"Table '{table}' columns: {columns}")


if __name__ == "__main__":
    probe_tables()
