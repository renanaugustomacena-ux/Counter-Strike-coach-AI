import argparse
import hashlib
import json
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

# --- Venv Guard ---
if sys.prefix == sys.base_prefix and not os.environ.get("CI"):
    print("ERROR: Not in venv. Run: source ~/.venvs/cs2analyzer/bin/activate", file=sys.stderr)
    sys.exit(2)

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
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
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
        "hash": "dim white",
        "path": "underline blue",
        "metric": "bold magenta",
    }
)

console = Console(theme=MTS_THEME)
install_rich_traceback(console=console)


# --- Logging (centralized) ---
from Programma_CS2_RENAN.observability.logger_setup import get_tool_logger

_tool_logger = get_tool_logger("audit_binaries", console=False)  # Rich owns stdout


class IndustrialBinaryAuditor:
    EXTENSIONS: Set[str] = {".dll", ".pyd", ".exe"}

    def __init__(self, target_dir: Optional[Path] = None):
        self.project_root = project_root
        self.logger = _tool_logger

        # Default target logic
        if target_dir:
            self.target_dir = Path(target_dir).absolute()
        else:
            # Fallback to standard PyInstaller locations
            self.target_dir = (self.project_root / "dist" / "Macena_CS2_Analyzer").absolute()
            if not self.target_dir.exists():
                # Try the simple name if the branded name doesn't exist
                self.target_dir = (self.project_root / "dist" / "cs2_analyzer").absolute()

        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, sig, frame):
        console.print(
            "\n[error]>>> Audit interrupted by user. Baselines may be incomplete.[/error]"
        )
        self.logger.warning("Audit interrupted by user SIGINT.")
        sys.exit(1)

    def calculate_sha256(self, file_path: Path) -> str:
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(8192), b""):  # Larger block size for binaries
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to hash {file_path}: {e}")
            raise

    def execute(self) -> bool:
        console.print(
            Panel.fit(
                "[bold cyan]MACENA MASTER BINARY AUDITOR[/bold cyan]\n[dim]Post-Build Security Validation & Integrity Locking[/dim]",
                border_style="blue",
            )
        )

        if not self.target_dir.exists():
            console.print(
                f"[warning]⚠️  Target directory not found:[/warning] [path]{self.target_dir}[/path]"
            )
            console.print(
                "[info]Skipping audit: No compiled distribution found. This is normal if you haven't run a build yet.[/info]"
            )
            self.logger.warning(f"Target directory missing: {self.target_dir}")
            return True  # Don't fail the pipeline if the build didn't happen yet (dev mode)

        try:
            display_path = self.target_dir.relative_to(self.project_root)
        except ValueError:
            display_path = self.target_dir

        console.print(f"[info]Scanning directory:[/info] [path]{display_path}[/path]")

        # 1. Gather files
        audit_files = []
        for root, _, files in os.walk(self.target_dir):
            for file in files:
                f_path = Path(root) / file
                if f_path.suffix.lower() in self.EXTENSIONS:
                    audit_files.append(f_path)

        if not audit_files:
            console.print(
                "[warning]No binaries (.exe, .dll, .pyd) found in target directory.[/warning]"
            )
            return True

        # 2. Process Files
        manifest = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "target": str(self.target_dir.name),
                "total_files": len(audit_files),
            },
            "binaries": {},
        }

        table = Table(
            title=f"Binary Security Snapshot ({len(audit_files)} files)", border_style="blue"
        )
        table.add_column("Binary Name", style="path")
        table.add_column("Type", style="info")
        table.add_column("SHA-256 Signature", style="hash")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Calculating signatures...", total=len(audit_files))

            for f_path in audit_files:
                rel_path = f_path.relative_to(self.target_dir)
                f_hash = self.calculate_sha256(f_path)

                manifest["binaries"][str(rel_path)] = f_hash

                # Only add to table if not too many files (to avoid scrolling)
                if len(audit_files) < 30:
                    table.add_row(f_path.name, f_path.suffix.upper(), f"{f_hash[:16]}...")

                self.logger.debug(f"Audited {rel_path}: {f_hash}")
                progress.update(task, advance=1)

        if len(audit_files) >= 30:
            console.print(
                f"[info]Snapshot contains {len(audit_files)} files. Detailed list suppressed (check log).[/info]"
            )
        else:
            console.print(table)

        # 3. Save Manifest
        output_path = self.target_dir / "binary_integrity.json"
        try:
            with open(output_path, "w") as f:
                json.dump(manifest, f, indent=4)
            console.print(
                f"\n✅ [success]Binary Integrity Locked[/success] -> [path]{output_path.name}[/path]"
            )
            self.logger.info(f"Binary manifest saved to {output_path}")
        except Exception as e:
            console.print(f"[error]Failed to save integrity manifest:[/error] {e}")
            self.logger.error(f"Manifest save failure: {e}")
            return False

        console.print(
            Panel(
                f"[bold green]AUDIT COMPLETE[/bold green]\nTotal Binaries: [metric]{len(audit_files)}[/metric]",
                border_style="green",
            )
        )
        return True


def main():
    parser = argparse.ArgumentParser(description="Macena Master Binary Auditor (MTS-IS)")
    parser.add_argument("dir", nargs="?", help="Specific directory to audit.")
    args = parser.parse_args()

    auditor = IndustrialBinaryAuditor(target_dir=args.dir)
    if not auditor.execute():
        sys.exit(1)


if __name__ == "__main__":
    main()
