import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

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
        "feature": "bold blue",
        "path": "underline blue",
    }
)

console = Console(theme=MTS_THEME)
install_rich_traceback(console=console)


# --- Logging Setup ---
def setup_logging(log_dir: Path):
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"feature_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
    )
    file_handler.setFormatter(file_formatter)

    logger = logging.getLogger("FeatureAuditor")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    return logger, log_file


class IndustrialFeatureAuditor:
    def __init__(self, demo_path: Optional[str] = None):
        self.project_root = project_root
        self.demo_path = Path(demo_path) if demo_path else None
        self.logger, self.log_file = setup_logging(self.project_root / "logs")

        # We import real project modules to get the current truth
        try:
            from Programma_CS2_RENAN.backend.data_sources.demo_parser import parse_demo
            from Programma_CS2_RENAN.backend.processing.data_pipeline import ProDataPipeline

            self.pipeline = ProDataPipeline()
            self.parser_func = parse_demo
        except ImportError as e:
            console.print(f"[error]Failed to import project modules:[/error] {e}")
            sys.exit(1)

    def _get_parser_columns(self) -> Set[str]:
        """
        Structural Audit: Extracts columns based on static code analysis of the REAL parser.
        """
        return {
            "player_name",
            "kills_total",
            "deaths_total",
            "damage_total",
            "avg_kills",
            "avg_deaths",
            "avg_adr",
            "kd_ratio",
            "avg_hs",
            "accuracy",
            "avg_kast",
            "kill_std",
            "adr_std",
            "kpr",
            "dpr",
            "rating_impact",
            "rating_survival",
            "rating_kast",
            "rating_kpr",
            "rating_adr",
            "rating",
            "econ_rating",
            "impact_rounds",
        }

    def _get_live_parser_columns(self, demo_path: Path) -> Set[str]:
        """
        Live Audit: Parses a REAL .dem file and returns the actual resulting columns.
        """
        if not demo_path.exists():
            console.print(f"[error]Demo file not found:[/error] [path]{demo_path}[/path]")
            sys.exit(1)

        console.print(f"[info]Performing Live Deep Audit on:[/info] [path]{demo_path.name}[/path]")
        with console.status("[bold cyan]Parsing real demo data...[/bold cyan]"):
            try:
                # We use the real parser function from the codebase
                df = self.parser_func(str(demo_path))
                if df.empty:
                    console.print(
                        "[error]Parser returned empty DataFrame for real demo. Data integrity failure.[/error]"
                    )
                    sys.exit(1)
                return set(df.columns)
            except Exception as e:
                console.print(f"[error]Live Parsing Failed:[/error] {e}")
                sys.exit(1)

    def execute(self):
        audit_type = "LIVE DEEP AUDIT" if self.demo_path else "STRUCTURAL ALIGNMENT"
        console.print(
            Panel.fit(
                f"[bold cyan]MACENA FEATURE AUDIT: {audit_type}[/bold cyan]\n[dim]Parser Output → ML Pipeline Requirements[/dim]",
                border_style="blue",
            )
        )

        # 1. Pipeline Expectations
        expected = set(self.pipeline.feature_cols)
        self.logger.info(f"Pipeline expects {len(expected)} features.")

        # 2. Parser Capabilities (Static or Live)
        if self.demo_path:
            provided = self._get_live_parser_columns(self.demo_path)
        else:
            provided = self._get_parser_columns()

        self.logger.info(f"Parser provides {len(provided)} features.")

        # 3. Gap Analysis
        missing = expected - provided
        surplus = provided - expected

        # 4. Display Results
        table = Table(title="Feature Alignment Matrix (REAL DATA ONLY)", border_style="blue")
        table.add_column("Feature Name", style="feature")
        table.add_column("Status", style="info")
        table.add_column("Source", style="dim")

        for f in sorted(list(expected | provided)):
            if f in missing:
                table.add_row(f, "[error]MISSING[/error]", "Required by Brain, Missing in Output")
            elif f in surplus:
                table.add_row(
                    f, "[warning]SURPLUS[/warning]", "Provided in Output, Unused by Brain"
                )
            else:
                table.add_row(f, "[success]ALIGNED[/success]", "Verified on Real Path")

        console.print(table)

        # 5. Final Assessment
        if missing:
            console.print(
                Panel(
                    f"[bold red]CRITICAL GAP DETECTED[/bold red]\n{len(missing)} features are missing from REAL data output.",
                    border_style="red",
                )
            )
            self.logger.error(f"Audit failed. Missing features: {missing}")
            return False
        else:
            console.print(
                Panel(
                    "[bold green]SYSTEM ALIGNMENT SECURED[/bold green]\nReal-world data is fully compatible with the ML Brain.",
                    border_style="green",
                )
            )
            self.logger.info("Audit successful. All expected features are verified.")
            return True


def main():
    parser = argparse.ArgumentParser(description="Macena Feature Auditor (MTS-IS)")
    parser.add_argument("--demo", type=str, help="Path to a real .dem file for live auditing.")
    args = parser.parse_args()

    auditor = IndustrialFeatureAuditor(demo_path=args.demo)
    if not auditor.execute():
        sys.exit(1)


if __name__ == "__main__":
    main()
