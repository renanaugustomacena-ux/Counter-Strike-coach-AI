"""Tests for StorageManager.archive_demo (STOR: best-effort archive contract).

archive_demo's docstring and its try/except around shutil.move establish the
contract that archiving is best-effort and must never raise: a failed archive
must not fail an otherwise-successful ingestion. The 2026-07-21 batch run
violated this — target_dir.mkdir(exist_ok=True) sat OUTSIDE the try block and
without parents=True, so a missing pro_ingest_dir parent (stale PRO_DEMO_PATH
pointing at an unmounted disk) raised FileNotFoundError AFTER all tick/event
data had landed, marking a fully-ingested demo as failed.
"""

from pathlib import Path

import pytest

from Programma_CS2_RENAN.backend.storage.storage_manager import StorageManager


@pytest.fixture()
def storage(tmp_path):
    """StorageManager with all paths rehomed under tmp_path."""
    s = StorageManager()
    s.local_path = tmp_path / "local"
    s.ingest_dir = s.local_path
    s.local_path.mkdir()
    return s


def _make_demo(tmp_path: Path) -> Path:
    demo = tmp_path / "team-a-vs-team-b-m1-dust2.dem"
    demo.write_bytes(b"PBDEMS2\x00fake")
    return demo


def test_archive_demo_missing_parent_does_not_raise(storage, tmp_path):
    """Missing pro_ingest_dir parent chain must not raise; demo stays put."""
    storage.pro_ingest_dir = tmp_path / "unmounted_disk" / "DEMO_PRO_PLAYERS"
    demo = _make_demo(tmp_path)

    storage.archive_demo(demo, is_pro=True)  # must not raise

    assert demo.exists(), "demo must remain in place when archiving fails"


def test_archive_demo_moves_into_ingested_when_dir_exists(storage, tmp_path):
    """Happy path: demo moves into <pro_ingest_dir>/ingested/."""
    storage.pro_ingest_dir = tmp_path / "DEMO_PRO_PLAYERS"
    storage.pro_ingest_dir.mkdir()
    demo = _make_demo(tmp_path)

    storage.archive_demo(demo, is_pro=True)

    target = storage.pro_ingest_dir / "ingested" / demo.name
    assert target.exists(), "demo must be moved into the ingested/ subfolder"
    assert not demo.exists(), "original demo path must be gone after the move"
