import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# --- Path Stabilization ---
script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# --- Windows Encoding Fix ---
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# --- Rich & Logging Imports ---
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import track
    from rich.table import Table
    from rich.theme import Theme
    from rich.traceback import install as install_rich_traceback
except ImportError:
    print("CRITICAL: 'rich' library not found. Please run 'pip install rich'.")
    sys.exit(1)

# --- Configuration ---
MTS_THEME = Theme(
    {
        "info": "cyan",
        "warning": "bold yellow",
        "error": "bold red",
        "success": "bold green",
        "hash": "dim green",
        "path": "underline blue",
    }
)

console = Console(theme=MTS_THEME)
install_rich_traceback(console=console)


# --- Logging Setup ---
def setup_logging(log_dir: Path):
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"manifest_gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
    )
    file_handler.setFormatter(file_formatter)

    logger = logging.getLogger("ManifestGen")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    return logger, log_file


class ManifestGenerator:
    # Critical files that define the system's identity
    CRITICAL_PATHS = [
        "Programma_CS2_RENAN/main.py",
        "Programma_CS2_RENAN/hltv_sync_service.py",
        "Programma_CS2_RENAN/backend/storage/database.py",
        "Programma_CS2_RENAN/backend/storage/db_models.py",
        # "Programma_CS2_RENAN/backend/processing/validation/dem_validator.py", # Removed (file missing in current tree)
        "Programma_CS2_RENAN/core/config.py",
        # "Programma_CS2_RENAN/core/localization.py", # Removed (likely missing)
        "Programma_CS2_RENAN/core/registry.py",
        "goliath.py",  # Added root authority
    ]

    def __init__(self):
        self.project_root = project_root
        self.logger, self.log_file = setup_logging(self.project_root / "logs")
        self.output_path = (
            self.project_root / "Programma_CS2_RENAN" / "core" / "integrity_manifest.json"
        )

    def calculate_sha256(self, file_path: Path) -> str:
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Hashing failed for {file_path}: {e}")
            raise

    def generate(self) -> bool:
        console.print(
            Panel.fit(
                "[bold cyan]MACENA INTEGRITY MANIFEST GENERATOR[/bold cyan]\n[dim]Creating cryptographic baseline for DevSecOps[/dim]",
                border_style="blue",
            )
        )

        manifest = {"generated_at": datetime.now().isoformat(), "version": "2.0", "hashes": {}}

        table = Table(title="Manifest Contents", border_style="blue")
        table.add_column("File Path", style="path")
        table.add_column("SHA-256 Hash", style="hash")
        table.add_column("Status", style="info")

        success_count = 0

        for path_str in track(
            self.CRITICAL_PATHS, description="[cyan]Hashing Critical Files...[/cyan]"
        ):
            full_path = self.project_root / path_str

            if full_path.exists():
                file_hash = self.calculate_sha256(full_path)
                manifest["hashes"][path_str] = file_hash
                table.add_row(path_str, f"{file_hash[:8]}...", "[success]Secured[/success]")
                self.logger.info(f"Hashed {path_str}: {file_hash}")
                success_count += 1
            else:
                table.add_row(path_str, "N/A", "[error]MISSING[/error]")
                self.logger.warning(f"File missing: {path_str}")
                console.print(f"[warning]⚠️  Warning: Critical file not found: {path_str}[/warning]")

        # Write to disk
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w") as f:
            json.dump(manifest, f, indent=4)

        console.print(table)

        if success_count == 0:
            console.print("[error]❌ FATAL: No critical files found. Manifest is empty.[/error]")
            return False

        console.print(
            Panel(
                f"[bold green]MANIFEST GENERATED SUCCESSFULLY[/bold green]\nSaved to: [path]{self.output_path.name}[/path]",
                border_style="green",
            )
        )
        self.logger.info(f"Manifest saved to {self.output_path}")
        return True


def main():
    generator = ManifestGenerator()
    success = generator.generate()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
