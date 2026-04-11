#!/usr/bin/env python3
"""
Goliath Hospital Diagnostic System v3.0

Comprehensive multi-department health diagnostic for the Macena CS2 Analyzer.
Each department specializes in a different aspect of project health:

  ER            - Syntax, forbidden patterns, namespace collisions
  Radiology     - Asset integrity (themes, map radars, models, layout)
  Pathology     - Data quality, mock data detection, DB data quality
  Cardiology    - Core health (critical modules, DB, config, analysis engines)
  Neurology     - ML/AI system (delegates to Ultimate_ML_Coach_Debugger)
  Oncology      - Tech debt (deprecated patterns, commented code, long functions)
  Pediatrics    - Recently modified files
  ICU           - Integration (import chains, service instantiation)
  Pharmacy      - Dependency health and version checks
  Tool Clinic   - Tool script validation
  Endocrinology - System integration (entry points, migrations, JSON configs)
"""

import ast
import importlib
import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from _infra import BaseValidator, Severity, path_stabilize

PROJECT_ROOT, SOURCE_ROOT = path_stabilize()

# =============================================================================
# CONSTANTS
# =============================================================================

EXCLUDE_DIRS = {
    "venv",
    "venv_win",
    "__pycache__",
    ".git",
    "node_modules",
    "dist",
    "build",
    "android_app",
    ".buildozer",
    "ios_app",
    "research",
    "mobile_app",
    "android",
    ".mypy_cache",
    ".pytest_cache",
    "eggs",
    "*.egg-info",
}

FORBIDDEN_PATTERNS = [
    r"/home/[a-z]+/Desktop",
    r"C:\\Users\\[A-Za-z]+\\Desktop",
    r'password\s*=\s*["\'][^"\']+["\']',
    r'api_key\s*=\s*["\'][^"\']+["\']',
]

MOCK_DATA_INDICATORS = [
    "mock",
    "fake",
    "dummy",
    "test_",
    "sample_",
    "placeholder",
    "FIXME",
    "TODO",
    "XXX",
    "HACK",
    "lorem ipsum",
    "12345",
    "example.com",
    "test@test",
    "foo",
    "bar",
    "baz",
]

DEPRECATED_PATTERNS = [
    (r'print\s*\(\s*f?["\']DEBUG', "Debug print in production"),
    (r"training_orchestrator\.py\.backup", "Backup file should be removed"),
]

CRITICAL_MODULES = [
    "Programma_CS2_RENAN/core/config.py",
    "Programma_CS2_RENAN/core/logger.py",
    "Programma_CS2_RENAN/core/asset_manager.py",
    "Programma_CS2_RENAN/core/session_engine.py",
    "Programma_CS2_RENAN/core/spatial_data.py",
    "Programma_CS2_RENAN/backend/storage/database.py",
    "Programma_CS2_RENAN/backend/storage/db_models.py",
    "Programma_CS2_RENAN/backend/storage/match_data_manager.py",
    "Programma_CS2_RENAN/backend/nn/model.py",
    "Programma_CS2_RENAN/backend/nn/jepa_model.py",
    "Programma_CS2_RENAN/backend/nn/coach_manager.py",
    "Programma_CS2_RENAN/backend/services/coaching_service.py",
    "Programma_CS2_RENAN/backend/services/analysis_orchestrator.py",
    "Programma_CS2_RENAN/backend/control/console.py",
    "Programma_CS2_RENAN/backend/processing/feature_engineering/vectorizer.py",
    "Programma_CS2_RENAN/backend/processing/tensor_factory.py",
    "Programma_CS2_RENAN/backend/analysis/__init__.py",
    "Programma_CS2_RENAN/backend/knowledge/experience_bank.py",
    "Programma_CS2_RENAN/backend/knowledge/graph.py",
    "Programma_CS2_RENAN/backend/ingestion/resource_manager.py",
    "Programma_CS2_RENAN/observability/logger_setup.py",
]

IMPORT_CHAINS = [
    ("Core Config", "Programma_CS2_RENAN.core.config", "get_setting"),
    ("Map Manager", "Programma_CS2_RENAN.core.map_manager", "MapManager"),
    ("Asset Manager", "Programma_CS2_RENAN.core.asset_manager", "AssetAuthority"),
    ("Spatial Data", "Programma_CS2_RENAN.core.spatial_data", "get_map_metadata"),
    ("Database", "Programma_CS2_RENAN.backend.storage.database", "get_db_manager"),
    ("DB Models", "Programma_CS2_RENAN.backend.storage.db_models", "PlayerMatchStats"),
    (
        "Match Data Mgr",
        "Programma_CS2_RENAN.backend.storage.match_data_manager",
        "get_match_data_manager",
    ),
    ("Model Factory", "Programma_CS2_RENAN.backend.nn.factory", "ModelFactory"),
    ("NN Config", "Programma_CS2_RENAN.backend.nn.config", "get_device"),
    (
        "Feature Extractor",
        "Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer",
        "FeatureExtractor",
    ),
    ("Tensor Factory", "Programma_CS2_RENAN.backend.processing.tensor_factory", "TensorFactory"),
    (
        "Coaching Service",
        "Programma_CS2_RENAN.backend.services.coaching_service",
        "CoachingService",
    ),
    (
        "Analysis Orchestrator",
        "Programma_CS2_RENAN.backend.services.analysis_orchestrator",
        "AnalysisOrchestrator",
    ),
    ("Hybrid Engine", "Programma_CS2_RENAN.backend.coaching.hybrid_engine", "HybridCoachingEngine"),
    ("Knowledge Graph", "Programma_CS2_RENAN.backend.knowledge.graph", "KnowledgeGraphManager"),
    (
        "Knowledge Retriever",
        "Programma_CS2_RENAN.backend.knowledge.rag_knowledge",
        "KnowledgeRetriever",
    ),
    ("Experience Bank", "Programma_CS2_RENAN.backend.knowledge.experience_bank", "ExperienceBank"),
    ("Role Classifier", "Programma_CS2_RENAN.backend.analysis.role_classifier", "RoleClassifier"),
    (
        "Win Probability",
        "Programma_CS2_RENAN.backend.analysis.win_probability",
        "WinProbabilityPredictor",
    ),
    ("Console", "Programma_CS2_RENAN.backend.control.console", "Console"),
    ("DB Governor", "Programma_CS2_RENAN.backend.control.db_governor", "DatabaseGovernor"),
    ("ML Controller", "Programma_CS2_RENAN.backend.control.ml_controller", "MLController"),
    ("Ingestion Manager", "Programma_CS2_RENAN.backend.control.ingest_manager", "IngestionManager"),
    ("Logger Setup", "Programma_CS2_RENAN.observability.logger_setup", "get_logger"),
]

ANALYSIS_FACTORIES = [
    "get_win_predictor",
    "get_role_classifier",
    "get_death_estimator",
    "get_deception_analyzer",
    "get_momentum_tracker",
    "get_entropy_analyzer",
    "get_game_tree_search",
    "get_blind_spot_detector",
    "get_engagement_range_analyzer",
    "get_utility_analyzer",
    "get_economy_optimizer",
]

CONTROL_MODULES = ["console.py", "db_governor.py", "ingest_manager.py", "ml_controller.py"]

REQUIRED_MAPS = [
    "de_dust2",
    "de_mirage",
    "de_inferno",
    "de_nuke",
    "de_ancient",
    "de_anubis",
    "de_vertigo",
]

# Files where long functions are expected by design
_ONCOLOGY_LENGTH_EXCLUSIONS = {
    "tools/Goliath_Hospital.py",
    "tools/Sanitize_Project.py",
    "tools/Feature_Audit.py",
    "tools/headless_validator.py",
    "tools/Ultimate_ML_Coach_Debugger.py",
    "tools/backend_validator.py",
    "tools/db_inspector.py",
    "tools/project_snapshot.py",
    "tests/conftest.py",
}

DEPARTMENT_NAMES = [
    "ER",
    "RADIOLOGY",
    "PATHOLOGY",
    "CARDIOLOGY",
    "NEUROLOGY",
    "ONCOLOGY",
    "PEDIATRICS",
    "ICU",
    "PHARMACY",
    "TOOL_CLINIC",
    "ENDOCRINOLOGY",
]


# =============================================================================
# GOLIATH HOSPITAL
# =============================================================================


class GoliathHospital(BaseValidator):
    """Comprehensive multi-department diagnostic for the Macena CS2 Analyzer."""

    TOTAL_SECTIONS = 11

    def __init__(self):
        super().__init__("Goliath Hospital Diagnostic System", version="3.0")

    # -----------------------------------------------------------------
    # BaseValidator hooks
    # -----------------------------------------------------------------

    def _add_extra_args(self, parser):
        parser.add_argument(
            "--department",
            "-d",
            type=str,
            choices=DEPARTMENT_NAMES,
            help="Run only a specific department",
        )

    def define_checks(self):
        dept = getattr(self.args, "department", None)
        dispatch = {
            "ER": self._check_er,
            "RADIOLOGY": self._check_radiology,
            "PATHOLOGY": self._check_pathology,
            "CARDIOLOGY": self._check_cardiology,
            "NEUROLOGY": self._check_neurology,
            "ONCOLOGY": self._check_oncology,
            "PEDIATRICS": self._check_pediatrics,
            "ICU": self._check_icu,
            "PHARMACY": self._check_pharmacy,
            "TOOL_CLINIC": self._check_tool_clinic,
            "ENDOCRINOLOGY": self._check_endocrinology,
        }
        if dept:
            idx = DEPARTMENT_NAMES.index(dept) + 1
            self.console.section(dept, idx, self.TOTAL_SECTIONS)
            dispatch[dept]()
        else:
            for i, name in enumerate(DEPARTMENT_NAMES, 1):
                self.console.section(name, i, self.TOTAL_SECTIONS)
                try:
                    dispatch[name]()
                except Exception as exc:
                    self.check(
                        name,
                        "department_run",
                        False,
                        error=f"Department crashed: {exc}",
                        severity=Severity.CRITICAL,
                    )

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _walk_py_files(root: Path):
        """Yield (relative_path_str, Path) for all .py files under root."""
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                if f.endswith(".py"):
                    fp = Path(dirpath) / f
                    yield str(fp.relative_to(PROJECT_ROOT)), fp

    def _run_with_timeout(self, func, timeout_sec=15, label="check"):
        """Run func in daemon thread with timeout. Returns (ok, result_or_error)."""
        result = [None, None]

        def _run():
            try:
                result[0] = func()
            except Exception as e:
                result[1] = e

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=timeout_sec)
        if t.is_alive():
            return False, f"{label} timed out after {timeout_sec}s"
        if result[1]:
            return False, str(result[1])
        return True, result[0]

    # =================================================================
    # 1. ER — Emergency Room
    # =================================================================

    def _check_er(self):
        for rel, fp in self._walk_py_files(SOURCE_ROOT):
            try:
                content = fp.read_text(encoding="utf-8")
            except Exception as e:
                self.check("ER", f"read:{rel}", False, error=str(e))
                continue

            # Syntax check
            try:
                ast.parse(content)
                syntax_ok = True
            except SyntaxError as e:
                syntax_ok = False
                self.check(
                    "ER",
                    f"syntax:{rel}",
                    False,
                    error=f"line {e.lineno}: {e.msg}",
                    severity=Severity.CRITICAL,
                )
            if syntax_ok:
                self.check("ER", f"syntax:{rel}", True, detail="parseable")

            # Forbidden patterns (skip self)
            if "Goliath_Hospital.py" not in rel:
                for pattern in FORBIDDEN_PATTERNS:
                    for i, line in enumerate(content.splitlines(), 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            self.check(
                                "ER",
                                f"forbidden:{rel}:{i}",
                                False,
                                error=f"Sensitive pattern: {pattern[:30]}...",
                                severity=Severity.ERROR,
                            )

            # Namespace collisions
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if (
                    stripped.startswith("from backend")
                    or stripped.startswith("from core")
                    or stripped.startswith("from ingestion")
                ):
                    if "Programma_CS2_RENAN" not in stripped:
                        self.check(
                            "ER",
                            f"namespace:{rel}:{i}",
                            False,
                            error=f"Bare import: {stripped[:50]}",
                            detail="Use Programma_CS2_RENAN prefix",
                            severity=Severity.ERROR,
                        )

    # =================================================================
    # 2. Radiology — Asset Integrity
    # =================================================================

    def _check_radiology(self):
        photo_gui = SOURCE_ROOT / "PHOTO_GUI"
        gui_exists = photo_gui.exists()
        self.check(
            "Radiology",
            "PHOTO_GUI_exists",
            gui_exists,
            error="PHOTO_GUI directory missing",
            severity=Severity.CRITICAL,
        )
        if not gui_exists:
            return

        # Themes
        for theme in ("cs2theme", "csgotheme", "cs16theme"):
            td = photo_gui / theme
            ok = td.exists()
            detail = ""
            if ok:
                count = len(list(td.glob("*")))
                ok = count >= 5
                detail = f"{count} assets"
            self.check(
                "Radiology",
                f"theme:{theme}",
                ok,
                error=f"Theme '{theme}' missing or sparse",
                detail=detail,
                severity=Severity.WARNING,
            )

        # Map radars
        maps_dir = photo_gui / "maps"
        if maps_dir.exists():
            map_files = list(maps_dir.glob("*.png")) + list(maps_dir.glob("*.jpg"))
            for m in REQUIRED_MAPS:
                found = any(m in f.stem for f in map_files)
                self.check(
                    "Radiology",
                    f"radar:{m}",
                    found,
                    error=f"Map radar for '{m}' not found",
                    severity=Severity.WARNING,
                )
        else:
            self.check(
                "Radiology",
                "maps_dir",
                False,
                error="PHOTO_GUI/maps directory not found",
                severity=Severity.ERROR,
            )

        # Models directory
        models_dir = SOURCE_ROOT / "models"
        if models_dir.exists():
            pt_count = len(list(models_dir.rglob("*.pt")))
            self.check("Radiology", "model_artifacts", True, detail=f"{pt_count} .pt files")
        else:
            self.check(
                "Radiology",
                "model_artifacts",
                True,
                detail="models/ not present (ok if no trained models yet)",
            )

        # layout.kv
        layout_kv = SOURCE_ROOT / "apps" / "desktop_app" / "layout.kv"
        self.check(
            "Radiology",
            "layout_kv",
            layout_kv.exists(),
            error="apps/desktop_app/layout.kv missing",
            severity=Severity.ERROR,
        )

    # =================================================================
    # 3. Pathology — Data Quality
    # =================================================================

    def _check_pathology(self):
        # Scan source for mock data indicators
        mock_count = 0
        clean_count = 0
        for rel, fp in self._walk_py_files(SOURCE_ROOT):
            try:
                content = fp.read_text(encoding="utf-8").lower()
            except Exception:
                continue
            has_mock = False
            for indicator in MOCK_DATA_INDICATORS:
                if indicator.lower() in content:
                    if "mock_data_indicators" not in content:
                        has_mock = True
                        break
            if has_mock:
                mock_count += 1
            else:
                clean_count += 1
        self.check(
            "Pathology",
            "mock_data_scan",
            True,
            detail=f"Files with mock indicators: {mock_count}, clean: {clean_count}",
        )

        # DB data quality (timeout-guarded)
        def _query_db():
            from sqlmodel import func, select

            from Programma_CS2_RENAN.backend.storage.database import get_db_manager
            from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

            db = get_db_manager()
            with db.get_session() as session:
                total = session.exec(select(func.count(PlayerMatchStats.id))).one()
                test_n = session.exec(
                    select(func.count(PlayerMatchStats.id)).where(
                        PlayerMatchStats.player_name.like("%test%")
                        | PlayerMatchStats.player_name.like("%mock%")
                        | PlayerMatchStats.player_name.like("%MCIV%")
                    )
                ).one()
            return total, test_n

        ok, result = self._run_with_timeout(_query_db, timeout_sec=15, label="DB data quality")
        if ok:
            total, test_n = result
            has_test = test_n > 0
            self.check(
                "Pathology",
                "db_data_quality",
                not has_test,
                error=f"{test_n}/{total} test/mock entries found",
                detail=f"{total} entries, no test data" if not has_test else "",
                severity=Severity.WARNING,
            )
        else:
            self.check(
                "Pathology",
                "db_data_quality",
                True,
                detail=f"Skipped: {result}",
                severity=Severity.INFO,
            )

    # =================================================================
    # 4. Cardiology — Core Health
    # =================================================================

    def _check_cardiology(self):
        # Critical modules exist
        for mod_path in CRITICAL_MODULES:
            full = PROJECT_ROOT / mod_path
            self.check(
                "Cardiology",
                f"module:{mod_path.split('/')[-1]}",
                full.exists(),
                error=f"Critical module missing: {mod_path}",
                severity=Severity.CRITICAL,
            )

        # DB connection
        def _db_conn():
            from sqlalchemy import text

            from Programma_CS2_RENAN.backend.storage.database import get_db_manager

            db = get_db_manager()
            with db.get_session() as s:
                s.execute(text("SELECT 1"))
            return True

        ok, result = self._run_with_timeout(_db_conn, timeout_sec=10, label="DB connection")
        self.check(
            "Cardiology",
            "db_connection",
            ok,
            error=f"DB connection failed: {result}" if not ok else "",
            detail="connected" if ok else "",
        )

        # Config loading
        try:
            from Programma_CS2_RENAN.core.config import get_setting

            theme = get_setting("THEME", default="cs2theme")
            self.check("Cardiology", "config_load", True, detail=f"THEME={theme}")
        except Exception as e:
            self.check("Cardiology", "config_load", False, error=str(e))

        # settings.json
        settings_path = SOURCE_ROOT / "settings.json"
        if settings_path.exists():
            try:
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                self.check("Cardiology", "settings_json", True, detail=f"{len(data)} keys")
            except json.JSONDecodeError as e:
                self.check("Cardiology", "settings_json", False, error=str(e))
        else:
            self.check(
                "Cardiology",
                "settings_json",
                False,
                error="settings.json not found",
                severity=Severity.WARNING,
            )

        # TemporalBaselineDecay
        def _baseline():
            from Programma_CS2_RENAN.backend.processing.baselines.pro_baseline import (
                TemporalBaselineDecay,
            )

            d = TemporalBaselineDecay()
            ref = datetime.now()
            return d.compute_weight(ref - timedelta(days=45), ref)

        ok, result = self._run_with_timeout(_baseline, timeout_sec=10, label="TemporalBaseline")
        if ok:
            w = result
            in_range = 0.1 <= w <= 1.0
            self.check(
                "Cardiology",
                "temporal_baseline",
                in_range,
                error=f"Weight out of range: {w}" if not in_range else "",
                detail=f"45-day weight: {w:.3f}" if in_range else "",
            )
        else:
            self.check(
                "Cardiology",
                "temporal_baseline",
                False,
                error=str(result),
                severity=Severity.WARNING,
            )

        # Analysis engine factories (data-driven)
        try:
            analysis_mod = importlib.import_module("Programma_CS2_RENAN.backend.analysis")
            ok_count = 0
            for fname in ANALYSIS_FACTORIES:
                fn = getattr(analysis_mod, fname, None)
                if fn is None:
                    continue
                try:
                    obj = fn()
                    if obj is not None:
                        ok_count += 1
                except Exception:
                    pass
            self.check(
                "Cardiology",
                "analysis_factories",
                ok_count == len(ANALYSIS_FACTORIES),
                error=(
                    f"Only {ok_count}/{len(ANALYSIS_FACTORIES)} operational"
                    if ok_count < len(ANALYSIS_FACTORIES)
                    else ""
                ),
                detail=f"{ok_count}/{len(ANALYSIS_FACTORIES)} operational",
                severity=Severity.WARNING,
            )
        except Exception as e:
            self.check(
                "Cardiology",
                "analysis_factories",
                False,
                error=f"Import failed: {e}",
                severity=Severity.WARNING,
            )

        # ResourceManager
        try:
            from Programma_CS2_RENAN.backend.ingestion.resource_manager import ResourceManager

            stats = ResourceManager.get_system_stats()
            ok_rm = isinstance(stats, dict) and "cpu" in stats
            self.check(
                "Cardiology",
                "resource_manager",
                ok_rm,
                error="Unexpected format" if not ok_rm else "",
                detail=f"CPU: {stats.get('cpu', 'N/A'):.1f}%" if ok_rm else "",
            )
        except Exception as e:
            self.check(
                "Cardiology", "resource_manager", False, error=str(e), severity=Severity.INFO
            )

        # Observability
        try:
            import logging

            from Programma_CS2_RENAN.observability.logger_setup import get_logger as _gl

            lg = _gl("cs2analyzer.goliath_test")
            self.check(
                "Cardiology",
                "observability",
                isinstance(lg, logging.Logger),
                error=f"Expected Logger, got {type(lg).__name__}",
            )
        except Exception as e:
            self.check(
                "Cardiology", "observability", False, error=str(e), severity=Severity.WARNING
            )

        # Control layer modules
        for cf in CONTROL_MODULES:
            path = SOURCE_ROOT / "backend" / "control" / cf
            self.check(
                "Cardiology", f"control:{cf}", path.exists(), error=f"Control module missing: {cf}"
            )

    # =================================================================
    # 5. Neurology — ML (delegates to Ultimate_ML_Coach_Debugger)
    # =================================================================

    def _check_neurology(self):
        try:
            from Ultimate_ML_Coach_Debugger import UltimateMLDebugger

            _ = UltimateMLDebugger()
            self.check(
                "Neurology",
                "ml_debugger_instantiation",
                True,
                detail="UltimateMLDebugger importable and instantiable",
            )
        except Exception as e:
            self.check(
                "Neurology",
                "ml_debugger_instantiation",
                False,
                error=f"Cannot instantiate ML debugger: {e}",
                severity=Severity.ERROR,
            )

    # =================================================================
    # 6. Oncology — Tech Debt
    # =================================================================

    def _check_oncology(self):
        dep_hits = 0
        comment_blocks = 0
        long_funcs = 0

        for rel, fp in self._walk_py_files(SOURCE_ROOT):
            try:
                content = fp.read_text(encoding="utf-8")
            except Exception:
                continue
            lines = content.splitlines()

            # Deprecated patterns
            for pattern, desc in DEPRECATED_PATTERNS:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line) and "DEPRECATED_PATTERNS" not in line:
                        dep_hits += 1
                        self.check(
                            "Oncology",
                            f"deprecated:{rel}:{i}",
                            False,
                            error=desc,
                            detail=line.strip()[:60],
                            severity=Severity.WARNING,
                        )

            # Commented-out code blocks (5+ consecutive)
            consecutive = 0
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("#") and re.match(
                    r"#\s*(def |class |import |from |if |for |while |return )", stripped
                ):
                    consecutive += 1
                else:
                    if consecutive >= 5:
                        comment_blocks += 1
                        self.check(
                            "Oncology",
                            f"commented_block:{rel}:{i - consecutive}",
                            False,
                            error=f"Commented code block ({consecutive} lines)",
                            severity=Severity.INFO,
                        )
                    consecutive = 0

            # Long functions (>100 lines)
            if any(rel.endswith(exc) for exc in _ONCOLOGY_LENGTH_EXCLUSIONS):
                continue
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if hasattr(node, "end_lineno") and node.end_lineno:
                        length = node.end_lineno - node.lineno
                        if length > 100:
                            long_funcs += 1
                            self.check(
                                "Oncology",
                                f"long_func:{rel}:{node.name}",
                                False,
                                error=f"'{node.name}' is {length} lines",
                                severity=Severity.WARNING,
                            )

        self.check(
            "Oncology",
            "tech_debt_summary",
            True,
            detail=(
                f"deprecated: {dep_hits}, comment blocks: {comment_blocks}, "
                f"long funcs: {long_funcs}"
            ),
        )

    # =================================================================
    # 7. Pediatrics — Recent Files
    # =================================================================

    def _check_pediatrics(self):
        now = datetime.now(timezone.utc)
        new_count = 0
        recent_count = 0

        for rel, fp in self._walk_py_files(SOURCE_ROOT):
            try:
                mtime = datetime.fromtimestamp(fp.stat().st_mtime, tz=timezone.utc)
            except Exception:
                continue
            age = now - mtime
            if age < timedelta(days=1):
                new_count += 1
            elif age < timedelta(days=7):
                recent_count += 1

        self.check(
            "Pediatrics",
            "recent_files",
            True,
            detail=f"New (<1 day): {new_count}, Recent (<7 days): {recent_count}",
        )

    # =================================================================
    # 8. ICU — Integration
    # =================================================================

    def _check_icu(self):
        # Import chain tests (data-driven)
        for name, module, attr in IMPORT_CHAINS:
            try:
                mod = importlib.import_module(module)
                has_attr = hasattr(mod, attr)
                self.check(
                    "ICU",
                    f"chain:{name}",
                    has_attr,
                    error=f"{attr} not found in {module}" if not has_attr else "",
                    detail=f"{attr} importable" if has_attr else "",
                )
            except Exception as e:
                self.check("ICU", f"chain:{name}", False, error=f"Import failed: {e}")

        # CoachingService instantiation
        def _coaching():
            from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

            _ = CoachingService()
            return True

        ok, result = self._run_with_timeout(_coaching, timeout_sec=15, label="CoachingService")
        self.check(
            "ICU",
            "coaching_service_init",
            ok,
            error=f"Failed: {result}" if not ok else "",
            detail="instantiated" if ok else "",
        )

        # FeatureExtractor + DB integration
        def _feat_extract():
            from sqlmodel import select

            from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
                FeatureExtractor,
            )
            from Programma_CS2_RENAN.backend.storage.database import get_db_manager
            from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

            fe = FeatureExtractor()
            db = get_db_manager()
            with db.get_session() as session:
                rec = session.exec(select(PlayerMatchStats).limit(1)).first()
            if rec is None:
                return "skip", None
            stats = {
                a: getattr(rec, a, 0)
                for a in vars(rec)
                if not a.startswith("_") and isinstance(getattr(rec, a, None), (int, float))
            }
            vec = fe.extract(stats)
            return "ok", len(vec) if hasattr(vec, "__len__") else "N/A"

        ok, result = self._run_with_timeout(
            _feat_extract, timeout_sec=20, label="FeatureExtractor+DB"
        )
        if ok:
            status, dim = result
            if status == "skip":
                self.check(
                    "ICU",
                    "feature_extraction",
                    True,
                    detail="Skipped (no data)",
                    severity=Severity.WARNING,
                )
            else:
                self.check("ICU", "feature_extraction", True, detail=f"Output dim: {dim}")
        else:
            self.check(
                "ICU", "feature_extraction", False, error=str(result), severity=Severity.WARNING
            )

    # =================================================================
    # 9. Pharmacy — Dependencies
    # =================================================================

    def _check_pharmacy(self):
        critical_deps = [
            ("torch", "PyTorch"),
            ("sqlmodel", "SQLModel"),
            ("numpy", "NumPy"),
            ("pandas", "Pandas"),
            ("sklearn", "Scikit-learn"),
        ]
        for package, name in critical_deps:
            try:
                mod = importlib.import_module(package)
                ver = getattr(mod, "__version__", "unknown")
                self.check("Pharmacy", f"dep:{package}", True, detail=f"{name} {ver}")
            except ImportError:
                self.check("Pharmacy", f"dep:{package}", False, error=f"{name} not installed")

        optional_deps = [
            ("sentence_transformers", "Sentence-Transformers"),
            ("ncps", "Neural Circuit Policies"),
            ("hflayers", "Hopfield Layers"),
            ("psutil", "PSUtil"),
        ]
        for package, name in optional_deps:
            try:
                importlib.import_module(package)
                self.check("Pharmacy", f"opt:{package}", True, detail=f"{name} available")
            except ImportError:
                self.check(
                    "Pharmacy",
                    f"opt:{package}",
                    False,
                    error=f"Optional: {name} not installed",
                    severity=Severity.WARNING,
                )

        # requirements.txt
        req = SOURCE_ROOT / "requirements.txt"
        if req.exists():
            lines = [l for l in req.read_text().splitlines() if l.strip() and not l.startswith("#")]
            self.check(
                "Pharmacy", "requirements_txt", True, detail=f"{len(lines)} dependencies listed"
            )
        else:
            self.check(
                "Pharmacy",
                "requirements_txt",
                False,
                error="requirements.txt not found",
                severity=Severity.WARNING,
            )

    # =================================================================
    # 10. Tool Clinic — Tool Validation
    # =================================================================

    def _check_tool_clinic(self):
        tool_dirs = [SOURCE_ROOT / "tools", PROJECT_ROOT / "tools"]
        tool_files: List[Path] = []
        for td in tool_dirs:
            if td.exists():
                tool_files.extend(td.rglob("*.py"))

        for tf in tool_files:
            rel = str(tf.relative_to(PROJECT_ROOT))
            try:
                content = tf.read_text(encoding="utf-8")
            except Exception as e:
                self.check("Tool Clinic", f"read:{rel}", False, error=str(e))
                continue

            # Syntax
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                self.check("Tool Clinic", f"syntax:{rel}", False, error=f"line {e.lineno}: {e.msg}")
                continue
            self.check("Tool Clinic", f"syntax:{rel}", True, detail="parseable")

            # Main guard
            has_main = "__name__" in content and "__main__" in content
            if not has_main:
                self.check(
                    "Tool Clinic",
                    f"main_guard:{rel}",
                    False,
                    error="Missing __main__ guard",
                    severity=Severity.WARNING,
                )

            # Module docstring
            has_doc = (
                tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
                and isinstance(tree.body[0].value.value, str)
            )
            if not has_doc:
                self.check(
                    "Tool Clinic",
                    f"docstring:{rel}",
                    False,
                    error="Missing module docstring",
                    severity=Severity.INFO,
                )

    # =================================================================
    # 11. Endocrinology — System Integration
    # =================================================================

    def _check_endocrinology(self):
        # Entry points
        for ep in ("main.py", "run_ingestion.py", "run_worker.py", "hltv_sync_service.py"):
            ep_path = SOURCE_ROOT / ep
            if not ep_path.exists():
                self.check("Endocrinology", f"entry:{ep}", False, error="Entry point not found")
                continue
            try:
                ast.parse(ep_path.read_text(encoding="utf-8"))
                self.check("Endocrinology", f"entry:{ep}", True, detail="parseable")
            except SyntaxError as e:
                self.check(
                    "Endocrinology",
                    f"entry:{ep}",
                    False,
                    error=f"Syntax error line {e.lineno}: {e.msg}",
                )

        # Alembic migration chain
        mig_dir = PROJECT_ROOT / "alembic" / "versions"
        if mig_dir.exists():
            mig_files = list(mig_dir.glob("*.py"))
            valid = 0
            for mf in mig_files:
                try:
                    ast.parse(mf.read_text(encoding="utf-8"))
                    valid += 1
                except SyntaxError:
                    self.check(
                        "Endocrinology",
                        f"migration:{mf.name}",
                        False,
                        error="Syntax error in migration",
                    )
            self.check(
                "Endocrinology",
                "alembic_migrations",
                valid == len(mig_files),
                detail=f"{valid}/{len(mig_files)} valid",
                severity=Severity.WARNING if valid < len(mig_files) else Severity.INFO,
            )
        else:
            self.check(
                "Endocrinology",
                "alembic_migrations",
                False,
                error="alembic/versions/ not found",
                severity=Severity.WARNING,
            )

        # JSON config validation
        json_configs = [
            ("settings.json", SOURCE_ROOT / "settings.json"),
            ("data/map_config.json", SOURCE_ROOT / "data" / "map_config.json"),
            ("data/map_tensors.json", SOURCE_ROOT / "data" / "map_tensors.json"),
        ]
        for name, path in json_configs:
            if not path.exists():
                self.check(
                    "Endocrinology",
                    f"json:{name}",
                    False,
                    error="Config not found",
                    severity=Severity.WARNING,
                )
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                detail = (
                    f"{len(data)} top-level keys" if isinstance(data, dict) else type(data).__name__
                )
                self.check("Endocrinology", f"json:{name}", True, detail=detail)
            except json.JSONDecodeError as e:
                self.check("Endocrinology", f"json:{name}", False, error=f"Invalid JSON: {e}")

        # Headless validator cross-reference
        hv = PROJECT_ROOT / "tools" / "headless_validator.py"
        if hv.exists():
            try:
                ast.parse(hv.read_text(encoding="utf-8"))
                self.check("Endocrinology", "headless_validator", True, detail="parseable")
            except SyntaxError:
                self.check(
                    "Endocrinology",
                    "headless_validator",
                    False,
                    error="Syntax error in headless_validator.py",
                )
        else:
            self.check(
                "Endocrinology",
                "headless_validator",
                False,
                error="headless_validator.py not found",
                severity=Severity.WARNING,
            )


# =============================================================================
# ENTRY POINT
# =============================================================================


if __name__ == "__main__":
    sys.exit(GoliathHospital().run())
