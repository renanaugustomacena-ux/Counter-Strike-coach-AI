"""DEPRECATED (R2-11): Use 'alembic upgrade head' for all schema migrations.

This tool only patches pre-Alembic databases by adding 5 columns to CoachState.
Since Alembic migrations 8c443d3d9523 and 3c6ecb5fe20e now manage this schema,
this script is retained only as an archive for historical reference.
"""

import argparse
import logging
import os
import sqlite3
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

# Emit deprecation warning on import
warnings.warn(
    "migrate_db.py is deprecated (R2-11). Use 'alembic upgrade head' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# --- Venv Guard ---
if sys.prefix == sys.base_prefix and not os.environ.get("CI"):
    print("ERROR: Not in venv. Run: source ~/.venvs/cs2analyzer/bin/activate", file=sys.stderr)
    sys.exit(2)

# --- When invoked directly, print notice and exit cleanly ---
if __name__ == "__main__":
    print("DEPRECATED (R2-11): migrate_db.py is superseded by Alembic.")
    print("Run instead: alembic upgrade head")
    print()
    print("This tool is retained as an archive for pre-Alembic databases only.")
    sys.exit(0)

# --- Path Stabilization ---
script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# --- Windows Encoding Fix ---
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# --- Rich Imports (optional — don't hard-fail on deprecated tool) ---
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm
    from rich.table import Table
    from rich.theme import Theme
    from rich.traceback import install as install_rich_traceback
except ImportError:
    Console = Panel = Confirm = Table = Theme = install_rich_traceback = None

# --- Configuration ---
MTS_THEME = Theme(
    {
        "info": "cyan",
        "warning": "bold yellow",
        "error": "bold red",
        "success": "bold green",
        "db": "bold blue",
        "path": "underline blue",
    }
)

console = Console(theme=MTS_THEME)
install_rich_traceback(console=console)


# --- Logging (centralized) ---
from Programma_CS2_RENAN.observability.logger_setup import get_tool_logger

_tool_logger = get_tool_logger("migrate_db", console=False)  # Rich owns stdout


class IndustrialDatabaseMigrator:
    # R2-11: DEPRECATED — these columns are now managed by Alembic migrations
    # (8c443d3d9523_triple_daemon_support + 3c6ecb5fe20e_add_fusion_plan_columns).
    # Retained only as a safety net for databases that predate Alembic adoption.
    REQUIRED_COLUMNS = [
        ("current_epoch", "INTEGER DEFAULT 0"),
        ("total_epochs", "INTEGER DEFAULT 0"),
        ("train_loss", "FLOAT DEFAULT 0.0"),
        ("val_loss", "FLOAT DEFAULT 0.0"),
        ("eta_seconds", "FLOAT DEFAULT 0.0"),
    ]

    def __init__(self, force: bool = False):
        self.project_root = project_root
        self.force = force
        self.logger = _tool_logger

        # Determine real DB path
        self.db_path = (
            self.project_root / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db"
        )
        self.backup_dir = self.project_root / "backups" / "database"

    def create_backup(self) -> Optional[Path]:
        """Creates a timestamped backup of the REAL database before migration.

        NN-82: Uses VACUUM INTO instead of shutil.copy2 to produce a
        consistent snapshot even when WAL mode is active with concurrent readers.
        """
        if not self.db_path.exists():
            return None

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"database_pre_migration_{timestamp}.db"

        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("VACUUM INTO ?", (str(backup_path),))
            conn.close()
            self.logger.info(f"Database backup created at {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            raise

    def get_missing_columns(
        self, conn: sqlite3.Connection, table_name: str
    ) -> Optional[List[Tuple[str, str]]]:
        """Audits the existing schema to find columns that need to be added.
        Returns None on failure (distinguishable from empty list = no missing columns)."""
        cursor = conn.cursor()
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = {row[1] for row in cursor.fetchall()}

            if not existing_columns:
                return []  # Table might not exist yet

            return [col for col in self.REQUIRED_COLUMNS if col[0] not in existing_columns]
        except Exception as e:
            self.logger.error(f"Schema audit failed: {e}")
            return None

    def migrate(self) -> bool:
        console.print(
            Panel.fit(
                "[bold cyan]MACENA INDUSTRIAL DB MIGRATOR[/bold cyan]\n[dim]Schema Evolution & Data Integrity Guard[/dim]",
                border_style="blue",
            )
        )
        # R2-11: Deprecation notice — prefer `alembic upgrade head`
        console.print(
            "[warning]NOTE: This tool is deprecated for schema migrations. "
            "Use 'alembic upgrade head' instead. This tool only patches "
            "pre-Alembic databases as a safety net.[/warning]"
        )

        if not self.db_path.exists():
            console.print(
                f"[warning]No database found at [path]{self.db_path}[/path]. Initializing fresh DB...[/warning]"
            )
            # In a real system, we'd call the initialization script.
            # For this tool, we only migrate existing ones.
            return True

        console.print(f"[info]Target Database:[/info] [path]{self.db_path}[/path]")

        # 1. Audit
        conn = sqlite3.connect(self.db_path)
        missing = self.get_missing_columns(conn, "coachstate")

        if missing is None:
            console.print("[error]Schema audit failed. Cannot determine migration plan.[/error]")
            conn.close()
            return False

        if not missing:
            console.print("[success]Schema is already up to date. No migration needed.[/success]")
            conn.close()
            return True

        # 2. Display Plan
        table = Table(title="Migration Plan (Table: coachstate)", border_style="blue")
        table.add_column("Column Name", style="db")
        table.add_column("Definition", style="dim")
        table.add_column("Status", style="warning")

        for col_name, col_def in missing:
            table.add_row(col_name, col_def, "PENDING")

        console.print(table)

        # 3. Confirmation & Backup
        if not self.force:
            if not Confirm.ask("\n[warning]Proceed with database schema modification?[/warning]"):
                console.print("[info]Migration cancelled.[/info]")
                conn.close()
                return False

        backup_path = None
        try:
            backup_path = self.create_backup()
            console.print(f"📦 [success]Backup Created:[/success] [dim]{backup_path.name}[/dim]")

            # 4. Execution
            cursor = conn.cursor()
            with console.status("[bold blue]Evolving schema...[/bold blue]"):
                for col_name, col_def in missing:
                    self.logger.info(f"Adding column {col_name} to coachstate")
                    cursor.execute(f"ALTER TABLE coachstate ADD COLUMN {col_name} {col_def}")
                    console.print(f"  [+] Added: [db]{col_name}[/db]")

                conn.commit()

            console.print(
                Panel(
                    "[bold green]MIGRATION SUCCESSFUL[/bold green]\nDatabase schema is now compatible with the current version.",
                    border_style="green",
                )
            )
            return True

        except Exception as e:
            console.print(
                Panel(
                    f"[bold red]MIGRATION FAILED[/bold red]\nError: {e}"
                    + (f"\n[info]A backup exists at: {backup_path}[/info]" if backup_path else ""),
                    border_style="red",
                )
            )
            self.logger.exception("Migration failed during execution.")
            conn.rollback()
            return False
        finally:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="Macena Database Migrator (MTS-IS)")
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Force migration without confirmation."
    )
    args = parser.parse_args()

    migrator = IndustrialDatabaseMigrator(force=args.yes)
    if not migrator.migrate():
        sys.exit(1)


if __name__ == "__main__":
    main()
