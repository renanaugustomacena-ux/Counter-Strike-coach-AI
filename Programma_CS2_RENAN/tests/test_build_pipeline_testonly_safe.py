"""F-0040 regression: --test-only must NEVER run Project Sanitization.

The old stage order ran `Sanitize_Project.py --yes` (deletes
database.db, hltv_metadata.db, match_data/, models/, logs/) BEFORE the
test_only early-return — so `console build run --test-only` and
verify_all_safe's special-cased invocation wiped live data."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# build_pipeline hard-exits without rich (CLI-only dep, absent on CI runners).
pytest.importorskip("rich", reason="build_pipeline requires rich (tools-only dep)")

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_pipeline_module():
    spec = importlib.util.spec_from_file_location(
        "build_pipeline_under_test", REPO_ROOT / "tools" / "build_pipeline.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_test_only_never_sanitizes():
    mod = _load_pipeline_module()
    pipe = mod.IndustrialBuildPipeline(test_only=True)
    stages = []
    pipe.run_stage = MagicMock(side_effect=lambda name, cmd: stages.append(name) or True)
    assert pipe.execute() is True
    assert "Project Sanitization" not in stages, "test-only ran the destructive stage"
    assert any("Unit Tests" in s for s in stages), "test-only must still run the tests"


def test_full_build_still_sanitizes_first():
    mod = _load_pipeline_module()
    pipe = mod.IndustrialBuildPipeline(test_only=False)
    stages = []
    pipe.run_stage = MagicMock(side_effect=lambda name, cmd: stages.append(name) or True)
    pipe.execute()
    assert stages and stages[0] == "Project Sanitization", "full build keeps sanitize as stage 1"
