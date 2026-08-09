"""Run directories must be unique per run and name the device actually used.

Heavy training runs on Linux/ROCm while inspection may happen on Windows CPU;
without the device in the run id a cheap smoke run is indistinguishable from a
real one in the dashboard.
"""

import os
import re

import pytest

from Programma_CS2_RENAN.backend.nn.tensorboard_callback import (
    build_run_dir,
    resolve_device_tag,
)

pytestmark = pytest.mark.timeout(60)


class TestDeviceTag:
    """Device tag reflects the accelerator actually available."""

    def test_returns_known_tag(self):
        assert resolve_device_tag() in {"cpu", "cuda", "rocm"}

    def test_cpu_when_no_gpu(self, monkeypatch):
        import torch

        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
        assert resolve_device_tag() == "cpu"


class TestRunDir:
    """Run directories are scoped by model type and stamped per run."""

    def test_contains_model_type_and_device(self):
        d = build_run_dir("jepa_pretrain")
        assert "jepa_pretrain" in d
        assert resolve_device_tag() in os.path.basename(d)

    def test_run_id_is_utc_timestamped(self):
        run_id = os.path.basename(build_run_dir("jepa_pretrain"))
        assert re.match(r"^\d{8}T\d{6}Z-(cpu|cuda|rocm)$", run_id), run_id

    def test_nested_under_runs_dir(self):
        from Programma_CS2_RENAN.core.config import RUNS_DIR

        d = build_run_dir("jepa_pretrain")
        assert os.path.normpath(d).startswith(os.path.normpath(RUNS_DIR))
