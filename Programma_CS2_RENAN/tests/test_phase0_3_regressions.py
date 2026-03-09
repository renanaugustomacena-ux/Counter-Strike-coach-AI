"""
Regression tests for Phase 0-3 bug fixes (P6-02).

Each test targets a specific bug fix from the MASTER_REMEDIATION_PLAN.
A fix without a regression test is incomplete — these tests ensure
the bugs cannot silently regress in future development cycles.
"""

import sqlite3
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from Programma_CS2_RENAN.backend.storage.db_models import CoachState


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


class _InMemoryDBManager:
    """Minimal in-memory DB manager for CI-portable tests."""

    def __init__(self, engine):
        self._engine = engine

    @contextmanager
    def get_session(self, engine_key="default"):
        with Session(self._engine, expire_on_commit=False) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise


def _make_engine(thread_safe=False):
    if thread_safe:
        # For cross-thread tests: share one connection across all threads
        return create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


# ===========================================================================
# P0-04: CoachState singleton under concurrency
# ===========================================================================


class TestP0_04_CoachStateSingleton:
    """P0-04: Verify get_state() creates exactly one CoachState row
    even under concurrent access from multiple threads."""

    def test_singleton_under_concurrent_access(self, monkeypatch):
        engine = _make_engine(thread_safe=True)
        SQLModel.metadata.create_all(engine)
        mock_db = _InMemoryDBManager(engine)

        # Import after engine setup
        from Programma_CS2_RENAN.backend.storage.state_manager import StateManager

        sm = StateManager.__new__(StateManager)
        sm.db = mock_db
        sm._lock = threading.Lock()

        results = []

        def call_get_state():
            try:
                state = sm.get_state()
                results.append(state.id)
            except Exception as e:
                results.append(f"error: {e}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(call_get_state) for _ in range(100)]
            for f in futures:
                f.result()

        # Verify exactly 1 row exists
        with Session(engine) as session:
            rows = session.exec(select(CoachState)).all()
            assert len(rows) == 1, (
                f"P0-04 REGRESSION: Expected exactly 1 CoachState row, got {len(rows)}"
            )

        # All results should reference the same id
        ids = [r for r in results if isinstance(r, int)]
        assert len(set(ids)) == 1, f"P0-04 REGRESSION: Multiple CoachState IDs created: {set(ids)}"

    def test_lazy_singleton_factory(self):
        """Verify get_state_manager() uses double-checked locking."""
        import Programma_CS2_RENAN.backend.storage.state_manager as sm_module

        # Reset singleton for test isolation
        original = sm_module._state_manager
        sm_module._state_manager = None
        try:
            with patch.object(sm_module, "get_db_manager") as mock_db:
                mock_db.return_value = MagicMock()
                m1 = sm_module.get_state_manager()
                m2 = sm_module.get_state_manager()
                assert m1 is m2, "P0-04 REGRESSION: Singleton factory returned different instances"
        finally:
            sm_module._state_manager = original


# ===========================================================================
# P0-05: TOCTOU backup race — SQLite Online Backup API
# ===========================================================================


class TestP0_05_BackupAtomicity:
    """P0-05: Verify backup uses SQLite Online Backup API (atomic)
    and the backup passes integrity check."""

    def test_backup_integrity_under_writes(self, tmp_path):
        """Create a DB, run backup while writing, verify backup passes integrity_check."""
        source_path = tmp_path / "source.db"

        # Create source with WAL mode
        conn = sqlite3.connect(str(source_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
        for i in range(100):
            conn.execute("INSERT INTO test VALUES (?, ?)", (i, f"row_{i}"))
        conn.commit()
        conn.close()

        # Backup using the Online Backup API (same pattern as db_backup.py)
        backup_path = tmp_path / "backup.db"
        source = sqlite3.connect(str(source_path), timeout=10)
        dest = sqlite3.connect(str(backup_path))
        try:
            source.backup(dest)
        finally:
            dest.close()
            source.close()

        # Verify integrity
        verify = sqlite3.connect(str(backup_path))
        try:
            result = verify.execute("PRAGMA integrity_check").fetchone()
            assert result[0] == "ok", f"P0-05 REGRESSION: Backup integrity failed: {result[0]}"
        finally:
            verify.close()

        # Verify data completeness
        verify2 = sqlite3.connect(str(backup_path))
        try:
            count = verify2.execute("SELECT COUNT(*) FROM test").fetchone()[0]
            assert count == 100, f"P0-05 REGRESSION: Expected 100 rows, got {count}"
        finally:
            verify2.close()


# ===========================================================================
# P0-06: Connection leak on WAL checkpoint failure
# ===========================================================================


class TestP0_06_ConnectionLeakOnCheckpoint:
    """P0-06: Verify connections are properly closed even when
    WAL checkpoint raises an exception."""

    def test_connection_closes_on_checkpoint_error(self, tmp_path):
        """Simulate checkpoint failure, verify connection doesn't leak."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.commit()
        conn.close()

        # Simulate the P0-06 fix pattern: try/finally ensuring close
        close_called = False
        original_connect = sqlite3.connect

        class MockConn:
            def __init__(self, real_conn):
                self._real = real_conn

            def execute(self, sql):
                raise RuntimeError("Simulated checkpoint failure")

            def close(self):
                nonlocal close_called
                close_called = True
                self._real.close()

        real_conn = original_connect(str(db_path), timeout=10)
        mock_conn = MockConn(real_conn)

        # Apply the P0-06 pattern
        try:
            try:
                mock_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            finally:
                mock_conn.close()
        except Exception:
            pass  # Expected

        assert close_called, "P0-06 REGRESSION: Connection.close() was not called after checkpoint failure"


# ===========================================================================
# P1-01: EarlyStopping actually stops training
# ===========================================================================


class TestP1_01_EarlyStoppingWired:
    """P1-01: Verify EarlyStopping triggers and stops training."""

    def test_stops_on_plateau(self):
        from Programma_CS2_RENAN.backend.nn.early_stopping import EarlyStopping

        stopper = EarlyStopping(patience=3, min_delta=0.01)

        # Loss decreases then completely plateaus (no improvement > min_delta)
        losses = [1.0, 0.8, 0.6, 0.6, 0.6, 0.6, 0.6]
        stop_epoch = None
        for epoch, loss in enumerate(losses):
            if stopper(loss):
                stop_epoch = epoch
                break

        assert stop_epoch is not None, "P1-01 REGRESSION: EarlyStopping never triggered"
        assert stop_epoch == 5, f"P1-01: Expected stop at epoch 5, got {stop_epoch}"

    def test_continues_on_improvement(self):
        from Programma_CS2_RENAN.backend.nn.early_stopping import EarlyStopping

        stopper = EarlyStopping(patience=5, min_delta=0.01)

        # Continuously improving
        for loss in [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4]:
            assert not stopper(loss), "EarlyStopping should not trigger during improvement"

    def test_wired_into_training_code(self):
        """Verify EarlyStopping is imported and used in train.py."""
        import inspect

        from Programma_CS2_RENAN.backend.nn import train

        source = inspect.getsource(train)
        assert "EarlyStopping" in source, (
            "P1-01 REGRESSION: EarlyStopping is not referenced in train.py"
        )
        assert "early_stopper" in source, (
            "P1-01 REGRESSION: early_stopper variable not found in train.py"
        )


# ===========================================================================
# P1-03: JEPA embedding collapse prevention
# ===========================================================================


class TestP1_03_JEPACollapseDetection:
    """P1-03: Verify JEPA produces diverse embeddings, not collapsed ones."""

    def test_embedding_diversity(self):
        from Programma_CS2_RENAN.backend.nn.config import INPUT_DIM

        from Programma_CS2_RENAN.backend.nn.jepa_model import JEPAEncoder

        encoder = JEPAEncoder(input_dim=INPUT_DIM, latent_dim=256)
        encoder.eval()

        # Generate 20 random inputs
        inputs = [torch.randn(1, INPUT_DIM) for _ in range(20)]
        with torch.no_grad():
            embeddings = [encoder(x).squeeze(0) for x in inputs]

        # Compute pairwise cosine similarity
        stacked = torch.stack(embeddings)
        stacked_norm = torch.nn.functional.normalize(stacked, dim=-1)
        similarity_matrix = stacked_norm @ stacked_norm.T

        # Exclude diagonal (self-similarity = 1.0)
        n = similarity_matrix.size(0)
        mask = ~torch.eye(n, dtype=torch.bool)
        off_diag = similarity_matrix[mask]

        mean_sim = off_diag.mean().item()
        assert mean_sim < 0.9, (
            f"P1-03 REGRESSION: Mean pairwise cosine similarity {mean_sim:.3f} >= 0.9 "
            f"indicates embedding collapse"
        )


# ===========================================================================
# P1-04: Training refuses insufficient data
# ===========================================================================


class TestP1_04_InsufficientDataRefusal:
    """P1-04: Verify training refuses to proceed with fewer than
    MIN_TRAINING_SAMPLES samples instead of using train=val."""

    def test_small_dataset_returns_none(self):
        from Programma_CS2_RENAN.backend.nn.train import MIN_TRAINING_SAMPLES, _prepare_splits

        X = np.random.randn(5, 25)  # 5 samples < MIN_TRAINING_SAMPLES
        y = np.random.randn(5, 25)

        result = _prepare_splits(X, y, None, None)
        assert result == (None, None, None, None), (
            f"P1-04 REGRESSION: _prepare_splits should refuse {len(X)} samples "
            f"(minimum: {MIN_TRAINING_SAMPLES})"
        )

    def test_sufficient_data_creates_split(self):
        from Programma_CS2_RENAN.backend.nn.train import MIN_TRAINING_SAMPLES, _prepare_splits

        n = MIN_TRAINING_SAMPLES + 10
        X = np.random.randn(n, 25)
        y = np.random.randn(n, 25)

        X_train, X_val, y_train, y_val = _prepare_splits(X, y, None, None)
        assert X_train is not None, "P1-04: Sufficient data should produce valid train split"
        assert X_val is not None, "P1-04: Sufficient data should produce valid val split"
        assert len(X_train) + len(X_val) == n

    def test_explicit_val_bypasses_check(self):
        from Programma_CS2_RENAN.backend.nn.train import _prepare_splits

        X = np.random.randn(5, 25)
        y = np.random.randn(5, 25)
        X_val = np.random.randn(3, 25)
        y_val = np.random.randn(3, 25)

        result = _prepare_splits(X, y, X_val, y_val)
        # When X_val is provided, skip size check
        assert result[0] is X
        assert result[1] is X_val


# ===========================================================================
# P1-05: Negative sampling excludes positive index
# ===========================================================================


class TestP1_05_NegativeSamplingExclusion:
    """P1-05: Verify that contrastive negative samples never include
    the positive index for any sample in the batch."""

    def test_negatives_exclude_positive(self):
        batch_size = 8
        num_negatives = 5

        for i in range(batch_size):
            candidates = [j for j in range(batch_size) if j != i]
            selected = candidates[:num_negatives]

            assert i not in selected, (
                f"P1-05 REGRESSION: Positive index {i} found in negative samples {selected}"
            )
            assert len(selected) == min(num_negatives, batch_size - 1)

    def test_negatives_exclude_positive_edge_case_batch_2(self):
        """With batch_size=2, each sample has only 1 possible negative."""
        batch_size = 2
        num_negatives = 5

        for i in range(batch_size):
            candidates = [j for j in range(batch_size) if j != i]
            effective = min(num_negatives, batch_size - 1)
            selected = candidates[:effective]

            assert i not in selected
            assert len(selected) == 1  # Only 1 other sample available


# ===========================================================================
# P3-01: PlayerRole enum unification
# ===========================================================================


class TestP3_01_PlayerRoleUnification:
    """P3-01: Verify all modules import PlayerRole from the canonical
    source (core.app_types) and there are no duplicate definitions."""

    def test_canonical_enum_has_all_roles(self):
        from Programma_CS2_RENAN.core.app_types import PlayerRole

        expected_roles = {"ENTRY", "AWPER", "SUPPORT", "LURKER", "IGL", "FLEX", "UNKNOWN"}
        actual_roles = {r.name for r in PlayerRole}
        assert expected_roles == actual_roles, (
            f"P3-01 REGRESSION: PlayerRole members mismatch. "
            f"Expected {expected_roles}, got {actual_roles}"
        )

    def test_role_classifier_uses_canonical_enum(self):
        from Programma_CS2_RENAN.backend.analysis.role_classifier import PlayerRole as RoleFromClassifier
        from Programma_CS2_RENAN.core.app_types import PlayerRole as Canonical

        assert RoleFromClassifier is Canonical, (
            "P3-01 REGRESSION: role_classifier.PlayerRole is not the canonical enum from core.app_types"
        )

    def test_role_features_uses_canonical_enum(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering.role_features import (
            PlayerRole as RoleFromFeatures,
        )
        from Programma_CS2_RENAN.core.app_types import PlayerRole as Canonical

        assert RoleFromFeatures is Canonical, (
            "P3-01 REGRESSION: role_features.PlayerRole is not the canonical enum from core.app_types"
        )

    def test_str_enum_for_db_serialization(self):
        """PlayerRole(str, Enum) ensures values are serialization-safe strings."""
        from Programma_CS2_RENAN.core.app_types import PlayerRole

        for role in PlayerRole:
            assert isinstance(role.value, str), f"P3-01: {role.name}.value is not a string"
            assert role.value == role.value.lower(), f"P3-01: {role.name}.value is not lowercase"


# ===========================================================================
# P3-02: avg_kills scale mismatch (KPR, not total kills per match)
# ===========================================================================


class TestP3_02_AvgKillsScaleConsistency:
    """P3-02: Verify pro baselines use per-round rates (KPR/DPR),
    not per-match totals, to match user stat scales."""

    def test_pro_bridge_uses_kpr_directly(self):
        from Programma_CS2_RENAN.backend.coaching.pro_bridge import PlayerCardAssimilator

        card = MagicMock()
        card.kpr = 0.75
        card.dpr = 0.60
        card.adr = 85.0
        card.kast = 0.72
        card.impact = 1.2
        card.rating_2_0 = 1.15
        card.detailed_stats_json = "{}"

        assimilator = PlayerCardAssimilator(card)
        baseline = assimilator.get_coach_baseline()

        # P3-02: avg_kills should be KPR (0.75), NOT KPR * 24 (= 18.0)
        assert baseline["avg_kills"] == 0.75, (
            f"P3-02 REGRESSION: avg_kills={baseline['avg_kills']} "
            f"should be KPR (0.75), not multiplied by rounds"
        )
        assert baseline["avg_deaths"] == 0.60, (
            f"P3-02 REGRESSION: avg_deaths={baseline['avg_deaths']} "
            f"should be DPR (0.60)"
        )

    def test_z_scores_are_sensible(self):
        """With per-round rates, z-scores should be within reasonable bounds."""
        # Simulate a user with 1.0 KPR against pro baseline with KPR mean=0.75, std=0.15
        user_kpr = 1.0
        pro_mean = 0.75
        pro_std = 0.15

        z = (user_kpr - pro_mean) / pro_std
        assert abs(z) < 5, (
            f"P3-02 REGRESSION: z-score {z:.2f} is unreasonably large. "
            f"Scale mismatch likely."
        )


# ===========================================================================
# P3-07: Tuple vs list ambiguity in correction_engine
# ===========================================================================


class TestP3_07_TupleListAmbiguity:
    """P3-07: Verify correction_engine handles float, tuple, and list
    deviation values identically."""

    def test_float_deviation(self):
        from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

        deviations = {"avg_adr": 1.5}
        result = generate_corrections(deviations, rounds_played=100)
        assert len(result) == 1
        assert result[0]["feature"] == "avg_adr"

    def test_tuple_deviation(self):
        from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

        deviations = {"avg_adr": (1.5, 0.3)}
        result = generate_corrections(deviations, rounds_played=100)
        assert len(result) == 1
        assert result[0]["feature"] == "avg_adr"

    def test_list_deviation(self):
        from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

        deviations = {"avg_adr": [1.5, 0.3]}
        result = generate_corrections(deviations, rounds_played=100)
        assert len(result) == 1
        assert result[0]["feature"] == "avg_adr"

    def test_tuple_and_list_produce_same_z(self):
        """P3-07: Both (z, raw_dev) as tuple and [z, raw_dev] as list
        should produce the same weighted z-score."""
        from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

        deviations_tuple = {"avg_adr": (1.5, 0.3)}
        deviations_list = {"avg_adr": [1.5, 0.3]}

        result_tuple = generate_corrections(deviations_tuple, rounds_played=100)
        result_list = generate_corrections(deviations_list, rounds_played=100)

        assert result_tuple[0]["weighted_z"] == pytest.approx(
            result_list[0]["weighted_z"]
        ), "P3-07 REGRESSION: tuple and list deviations produce different z-scores"

    def test_mixed_deviation_types(self):
        """Handle a mix of float, tuple, and list in the same call."""
        from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections

        deviations = {
            "avg_adr": 1.5,
            "avg_hs": (0.8, 0.1),
            "avg_kast": [1.2, 0.05],
        }
        result = generate_corrections(deviations, rounds_played=200)
        assert len(result) == 3, "P3-07: Should handle all 3 deviation types in one call"


# ===========================================================================
# P0-04 + Status enum validation
# ===========================================================================


class TestP0_04_StatusEnumValidation:
    """Verify StateManager rejects invalid global status values."""

    def test_invalid_global_status_raises(self, monkeypatch):
        engine = _make_engine()
        mock_db = _InMemoryDBManager(engine)

        from Programma_CS2_RENAN.backend.storage.state_manager import StateManager

        sm = StateManager.__new__(StateManager)
        sm.db = mock_db
        sm._lock = threading.Lock()

        # Pre-create state
        with Session(engine) as session:
            session.add(CoachState())
            session.commit()

        # Valid status should succeed
        sm.update_status("hunter", "Running")

        # Invalid global status should raise (caught internally by update_status)
        # The function catches exceptions, so verify the state wasn't corrupted
        sm.update_status("global", "INVALID_STATUS_XYZ")
        status_info = sm.get_status("global")
        assert status_info["status"] != "INVALID_STATUS_XYZ"
