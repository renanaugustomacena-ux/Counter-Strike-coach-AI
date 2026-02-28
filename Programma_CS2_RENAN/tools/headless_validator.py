#!/usr/bin/env python3
"""
Headless System Validator — Post-task regression gate for Macena CS2 Analyzer.

Authority: CLAUDE.md Dev Rule 9, /validate skill (7 phases).

Phases:
  1. Environment   — project root, critical directories
  2. Core Imports   — config, spatial_data, session_engine, lifecycle
  3. Backend Imports — storage, processing, analysis, coaching, services
  4. Database Schema — in-memory SQLite validation
  5. Config Loading  — settings.json, map_config.json
  6. ML Smoke        — ModelFactory, JEPA, feature dimensions
  7. Observability   — logger setup, telemetry

Exit codes: 0 = PASS, 1 = FAIL
Constraint: must complete in < 20 seconds.
"""

import json
import sys
from pathlib import Path

from _infra import PROJECT_ROOT, SOURCE_ROOT, BaseValidator, Severity


class HeadlessValidator(BaseValidator):
    """Lightweight regression gate — verifies the codebase is not broken."""

    def __init__(self):
        super().__init__("Macena Headless Validator", version="1.0")

    def define_checks(self):
        self._phase_environment()
        self._phase_core_imports()
        self._phase_backend_imports()
        self._phase_database_schema()
        self._phase_config_loading()
        self._phase_ml_smoke()
        self._phase_observability()

    # ------------------------------------------------------------------
    # Phase 1: Environment
    # ------------------------------------------------------------------
    def _phase_environment(self):
        self.console.section("Environment", 1, 7)

        self.check(
            "Environment", "PROJECT_ROOT exists", PROJECT_ROOT.exists(), detail=str(PROJECT_ROOT)
        )

        self.check(
            "Environment", "SOURCE_ROOT exists", SOURCE_ROOT.exists(), detail=str(SOURCE_ROOT)
        )

        for d in ["apps", "backend", "core", "ingestion", "observability", "reporting"]:
            self.check("Environment", f"Directory: {d}", (SOURCE_ROOT / d).is_dir())

        self.check(
            "Environment",
            "Python >= 3.10",
            sys.version_info >= (3, 10),
            detail=f"{sys.version_info.major}.{sys.version_info.minor}",
        )

    # ------------------------------------------------------------------
    # Phase 2: Core Imports
    # ------------------------------------------------------------------
    def _phase_core_imports(self):
        self.console.section("Core Imports", 2, 7)

        modules = [
            ("core.config", "Programma_CS2_RENAN.core.config"),
            ("core.spatial_data", "Programma_CS2_RENAN.core.spatial_data"),
            ("core.session_engine", "Programma_CS2_RENAN.core.session_engine"),
            ("core.lifecycle", "Programma_CS2_RENAN.core.lifecycle"),
            ("core.asset_manager", "Programma_CS2_RENAN.core.asset_manager"),
            ("core.map_manager", "Programma_CS2_RENAN.core.map_manager"),
            ("core.spatial_engine", "Programma_CS2_RENAN.core.spatial_engine"),
        ]
        for label, mod_path in modules:
            ok = self._try_import(mod_path)
            self.check("Core Imports", label, ok)

    # ------------------------------------------------------------------
    # Phase 3: Backend Imports
    # ------------------------------------------------------------------
    def _phase_backend_imports(self):
        self.console.section("Backend Imports", 3, 7)

        modules = [
            ("storage.database", "Programma_CS2_RENAN.backend.storage.database"),
            ("storage.db_models", "Programma_CS2_RENAN.backend.storage.db_models"),
            (
                "processing.vectorizer",
                "Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer",
            ),
            (
                "processing.pro_baseline",
                "Programma_CS2_RENAN.backend.processing.baselines.pro_baseline",
            ),
            ("analysis.__init__", "Programma_CS2_RENAN.backend.analysis"),
            ("analysis.belief_model", "Programma_CS2_RENAN.backend.analysis.belief_model"),
            ("analysis.momentum", "Programma_CS2_RENAN.backend.analysis.momentum"),
            ("coaching.hybrid_engine", "Programma_CS2_RENAN.backend.coaching.hybrid_engine"),
            ("services.coaching_service", "Programma_CS2_RENAN.backend.services.coaching_service"),
            ("services.analysis_service", "Programma_CS2_RENAN.backend.services.analysis_service"),
            ("nn.factory", "Programma_CS2_RENAN.backend.nn.factory"),
            ("nn.jepa_model", "Programma_CS2_RENAN.backend.nn.jepa_model"),
            ("nn.rap_coach.model", "Programma_CS2_RENAN.backend.nn.rap_coach.model"),
            ("knowledge.rag_knowledge", "Programma_CS2_RENAN.backend.knowledge.rag_knowledge"),
            ("knowledge.experience_bank", "Programma_CS2_RENAN.backend.knowledge.experience_bank"),
        ]
        for label, mod_path in modules:
            ok = self._try_import(mod_path)
            self.check("Backend Imports", label, ok)

    # ------------------------------------------------------------------
    # Phase 4: Database Schema
    # ------------------------------------------------------------------
    def _phase_database_schema(self):
        self.console.section("Database Schema", 4, 7)

        try:
            from sqlmodel import Session, SQLModel, create_engine, select

            import Programma_CS2_RENAN.backend.storage.db_models  # noqa: F401 — registers tables

            # F8-07: Schema validation uses in-memory SQLite for speed. Does not test WAL mode,
            # busy timeouts, or concurrent access. Full production DB validation: backend_validator.py.
            engine = create_engine("sqlite:///:memory:")
            SQLModel.metadata.create_all(engine)

            tables = list(SQLModel.metadata.tables.keys())
            self.check(
                "Database",
                "In-memory schema creation",
                len(tables) > 0,
                detail=f"{len(tables)} tables",
            )

            required = [
                "playerprofile",
                "coachinginsight",
                "playermatchstats",
                "playertickstate",
                "coachstate",
                "roundstats",
            ]
            for t in required:
                self.check("Database", f"Table registered: {t}", t in tables)

            # CRUD smoke on in-memory
            from Programma_CS2_RENAN.backend.storage.db_models import CoachState

            with Session(engine) as session:
                session.exec(select(CoachState)).all()
            self.check("Database", "In-memory CRUD smoke", True)

        except Exception as e:
            self.check("Database", "Schema validation", False, error=str(e))

    # ------------------------------------------------------------------
    # Phase 5: Config Loading
    # ------------------------------------------------------------------
    def _phase_config_loading(self):
        self.console.section("Config Loading", 5, 7)

        # user_settings.json
        settings_path = SOURCE_ROOT / "user_settings.json"
        if settings_path.exists():
            try:
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                self.check(
                    "Config",
                    "user_settings.json parsable",
                    isinstance(data, dict),
                    detail=f"{len(data)} keys",
                )
            except Exception as e:
                self.check("Config", "user_settings.json", False, error=str(e))
        else:
            self.check(
                "Config",
                "user_settings.json exists",
                False,
                severity=Severity.WARNING,
                error="File missing (first-run expected)",
            )

        # map_config.json
        map_cfg = SOURCE_ROOT / "data" / "map_config.json"
        if map_cfg.exists():
            try:
                data = json.loads(map_cfg.read_text(encoding="utf-8"))
                self.check(
                    "Config",
                    "map_config.json parsable",
                    isinstance(data, dict) and len(data) > 0,
                    detail=f"{len(data)} maps",
                )
            except Exception as e:
                self.check("Config", "map_config.json", False, error=str(e))
        else:
            self.check("Config", "map_config.json exists", False)

        # METADATA_DIM consistency
        try:
            from Programma_CS2_RENAN.backend.nn.config import INPUT_DIM
            from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

            self.check("Config", "METADATA_DIM > 0", METADATA_DIM > 0, detail=f"dim={METADATA_DIM}")
            self.check(
                "Config",
                "INPUT_DIM == METADATA_DIM",
                INPUT_DIM == METADATA_DIM,
                detail=f"INPUT_DIM={INPUT_DIM}, METADATA_DIM={METADATA_DIM}",
            )
        except Exception as e:
            self.check("Config", "Dimension consistency", False, error=str(e))

    # ------------------------------------------------------------------
    # Phase 6: ML Smoke
    # ------------------------------------------------------------------
    def _phase_ml_smoke(self):
        self.console.section("ML Smoke", 6, 7)

        try:
            import torch

            self.check("ML", "PyTorch importable", True, detail=f"v{torch.__version__}")
        except ImportError:
            self.check("ML", "PyTorch importable", False)
            return

        import torch

        try:
            from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
            from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

            # Test each model type
            model_types = {
                "default": {"input_dim": METADATA_DIM, "output_dim": 4},
                "jepa": {"input_dim": METADATA_DIM, "output_dim": METADATA_DIM, "latent_dim": 128},
                "vl-jepa": {
                    "input_dim": METADATA_DIM,
                    "output_dim": METADATA_DIM,
                    "latent_dim": 128,
                },
                "role_head": {},
            }

            for mtype, kwargs in model_types.items():
                try:
                    model = ModelFactory.get_model(mtype, **kwargs)
                    self.check(
                        "ML",
                        f"ModelFactory '{mtype}'",
                        model is not None,
                        detail=type(model).__name__,
                    )
                except Exception as e:
                    self.check("ML", f"ModelFactory '{mtype}'", False, error=str(e))

            # Feature extractor
            from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
                FeatureExtractor,
            )

            fe = FeatureExtractor()
            self.check(
                "ML",
                "FeatureExtractor instantiation",
                fe is not None,
                detail=f"output_dim={METADATA_DIM}",
            )

        except Exception as e:
            self.check("ML", "ML subsystem", False, error=str(e))

    # ------------------------------------------------------------------
    # Phase 7: Observability
    # ------------------------------------------------------------------
    def _phase_observability(self):
        self.console.section("Observability", 7, 7)

        # Logger setup
        try:
            from Programma_CS2_RENAN.observability.logger_setup import get_logger

            logger = get_logger("cs2analyzer.headless_test")
            self.check("Observability", "get_logger()", logger is not None, detail=logger.name)
        except Exception as e:
            self.check("Observability", "get_logger()", False, error=str(e))

        # Telemetry module
        ok = self._try_import("Programma_CS2_RENAN.observability.telemetry")
        self.check(
            "Observability",
            "telemetry module",
            ok,
            severity=Severity.WARNING if not ok else Severity.INFO,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _try_import(module_path: str) -> bool:
        try:
            __import__(module_path)
            return True
        except Exception:
            return False


if __name__ == "__main__":
    validator = HeadlessValidator()
    sys.exit(validator.run())
