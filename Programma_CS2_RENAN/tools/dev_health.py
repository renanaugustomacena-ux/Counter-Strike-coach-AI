#!/usr/bin/env python3
"""
Development Health Check — Pre-commit hook and full health runner.

Modes:
  --quick : Fast subset (import smoke + DB alive + config valid) for pre-commit (< 10s)
  --full  : Runs headless_validator + backend_validator in sequence

Exit codes: 0 = PASS, 1 = FAIL
"""

import json
import subprocess
import sys
from pathlib import Path

from _infra import PROJECT_ROOT, SOURCE_ROOT, BaseValidator, Severity


class DevHealthCheck(BaseValidator):

    def __init__(self):
        super().__init__("Development Health Check", version="1.0")
        self._mode = "quick"

    def _add_extra_args(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--quick",
            action="store_true",
            default=True,
            help="Fast subset for pre-commit (default)",
        )
        group.add_argument(
            "--full", action="store_true", help="Full health: headless + backend validators"
        )

    def define_checks(self):
        if getattr(self.args, "full", False):
            self._mode = "full"
            self._run_full()
        else:
            self._run_quick()

    # ------------------------------------------------------------------
    # Quick mode: lightweight checks for pre-commit speed
    # ------------------------------------------------------------------
    def _run_quick(self):
        self.console.section("Quick Health (Pre-Commit)", 1, 1)

        # 1. Critical imports
        critical_modules = [
            "Programma_CS2_RENAN.core.config",
            "Programma_CS2_RENAN.backend.storage.database",
            "Programma_CS2_RENAN.backend.storage.db_models",
            "Programma_CS2_RENAN.backend.nn.factory",
            "Programma_CS2_RENAN.backend.services.coaching_service",
            "Programma_CS2_RENAN.observability.logger_setup",
        ]
        for mod in critical_modules:
            ok = self._try_import(mod)
            self.check("Quick", f"Import: {mod.split('.')[-1]}", ok)

        # 2. Config parsable
        settings = SOURCE_ROOT / "user_settings.json"
        if settings.exists():
            try:
                data = json.loads(settings.read_text(encoding="utf-8"))
                self.check("Quick", "user_settings.json valid", isinstance(data, dict))
            except Exception as e:
                self.check("Quick", "user_settings.json", False, error=str(e))
        else:
            self.check("Quick", "user_settings.json exists", False, severity=Severity.WARNING)

        map_cfg = SOURCE_ROOT / "data" / "map_config.json"
        if map_cfg.exists():
            try:
                data = json.loads(map_cfg.read_text(encoding="utf-8"))
                self.check(
                    "Quick", "map_config.json valid", isinstance(data, dict) and len(data) > 0
                )
            except Exception as e:
                self.check("Quick", "map_config.json", False, error=str(e))
        else:
            self.check("Quick", "map_config.json exists", False)

        # 3. DB alive (in-memory schema creation)
        try:
            from sqlmodel import SQLModel, create_engine

            import Programma_CS2_RENAN.backend.storage.db_models  # noqa: F401

            engine = create_engine("sqlite:///:memory:")
            SQLModel.metadata.create_all(engine)
            tables = list(SQLModel.metadata.tables.keys())
            self.check("Quick", "In-memory schema", len(tables) > 5, detail=f"{len(tables)} tables")
        except Exception as e:
            self.check("Quick", "DB schema smoke", False, error=str(e))

    # ------------------------------------------------------------------
    # Full mode: delegate to headless + backend validators
    # ------------------------------------------------------------------
    def _run_full(self):
        self.console.section("Full Health Suite", 1, 1)

        tools_dir = SOURCE_ROOT / "tools"
        validators = [
            ("headless_validator.py", "Headless Validator"),
            ("backend_validator.py", "Backend Validator"),
        ]

        for script, label in validators:
            script_path = tools_dir / script
            if not script_path.exists():
                self.check("Full", label, False, error=f"{script} not found")
                continue

            try:
                result = subprocess.run(
                    [sys.executable, str(script_path), "--quiet"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(tools_dir),
                )
                self.check(
                    "Full",
                    label,
                    result.returncode == 0,
                    detail=f"exit={result.returncode}",
                    error=result.stderr[:200] if result.returncode != 0 else "",
                )
            except subprocess.TimeoutExpired:
                self.check("Full", label, False, error="Timed out after 120s")
            except Exception as e:
                self.check("Full", label, False, error=str(e))

    @staticmethod
    def _try_import(module_path: str) -> bool:
        try:
            __import__(module_path)
            return True
        except Exception:
            return False


if __name__ == "__main__":
    checker = DevHealthCheck()
    sys.exit(checker.run())
