# TensorBoard JEPA Structure Instrumentation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make TensorBoard a working instrument that detects JEPA representation collapse and lets the embedding space be explored.

**Architecture:** A new pure-function module computes collapse metrics from an embedding matrix. `TensorBoardCallback` owns the single `SummaryWriter`, captures a fixed probe batch at train start, and logs those metrics each epoch. The already-written but orphaned `EmbeddingProjector` is constructed with that same writer and registered alongside it, fixing event-file fragmentation.

**Tech Stack:** Python 3.12.10, PyTorch (`>=2.1.0,<3.0`), `tensorboard==2.21.0`, pytest.

**Spec:** `docs/superpowers/specs/2026-08-09-tensorboard-jepa-structure-design.md`

## Global Constraints

- **Never run heavy training on CPU.** Windows is CPU-only here (`torch 2.13.0+cpu`); ROCm/PyTorch is Linux-only. All tests in this plan are cheap CPU unit tests — that is fine. Do not start a training run to validate anything.
- **`PYTHONUTF8=1` is required** for every Python command on Windows. Without it, dependency builds and any non-ASCII output crash under cp1252.
- **No change to training dynamics** — loss, optimizer, schedule, and architecture must be untouched. Wiring edits to `jepa_train.py` are in scope; they must not alter what the model computes.
- **Tests live in `Programma_CS2_RENAN/tests/`.** `pytest.ini` sets `testpaths = tests Programma_CS2_RENAN/tests`.
- **Test command (Windows, from repo root):**
  `PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest <path> -v`
  On Linux: `python -m pytest <path> -v`.
- **Commit style:** conventional commits (`feat:`, `fix:`, `test:`, `chore:`).
- **Callback errors never crash training** — `CallbackRegistry.fire` catches and logs. Do not rely on exceptions propagating out of hooks.

---

### Task 1: Collapse metrics module

Pure functions with no TensorBoard import and no model coupling, so they are testable without a writer, a training loop, or a GPU.

**Files:**
- Create: `Programma_CS2_RENAN/backend/nn/collapse_metrics.py`
- Test: `Programma_CS2_RENAN/tests/test_collapse_metrics.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `compute_collapse_metrics(embeddings: torch.Tensor) -> dict[str, float]` returning exactly the keys `"std_mean"`, `"std_min"`, `"effective_rank"`, `"cosine_offdiag_mean"`.
  - `compute_ema_drift(online_params: Iterable[torch.Tensor], target_params: Iterable[torch.Tensor]) -> float`.

- [ ] **Step 1: Write the failing test**

Create `Programma_CS2_RENAN/tests/test_collapse_metrics.py`:

```python
"""Unit tests for JEPA representation-collapse metrics.

Deterministic, CPU-only, no TensorBoard required.
"""

import torch

from Programma_CS2_RENAN.backend.nn.collapse_metrics import (
    compute_collapse_metrics,
    compute_ema_drift,
)


def _collapsed(n=64, d=16):
    """All rows point in essentially the same direction."""
    torch.manual_seed(0)
    base = torch.randn(1, d)
    return base.repeat(n, 1) + 1e-6 * torch.randn(n, d)


def _healthy(n=64, d=16):
    """Rows spread across many directions."""
    torch.manual_seed(0)
    return torch.randn(n, d)


class TestCollapseMetrics:
    def test_returns_expected_keys(self):
        m = compute_collapse_metrics(_healthy())
        assert set(m) == {
            "std_mean",
            "std_min",
            "effective_rank",
            "cosine_offdiag_mean",
        }
        assert all(isinstance(v, float) for v in m.values())

    def test_collapsed_embeddings_flagged(self):
        m = compute_collapse_metrics(_collapsed())
        assert m["std_mean"] < 0.01
        assert m["std_min"] < 0.01
        assert m["cosine_offdiag_mean"] > 0.99
        assert m["effective_rank"] < 1.5

    def test_healthy_embeddings_not_flagged(self):
        m = compute_collapse_metrics(_healthy(n=64, d=16))
        assert m["std_mean"] > 0.05
        assert abs(m["cosine_offdiag_mean"]) < 0.3
        assert m["effective_rank"] > 8.0

    def test_scale_invariance(self):
        e = _healthy()
        a = compute_collapse_metrics(e)
        b = compute_collapse_metrics(e * 37.0)
        for k in a:
            assert abs(a[k] - b[k]) < 1e-4

    def test_flattens_higher_rank_input(self):
        e = torch.randn(8, 5, 16)  # [B, T, D]
        m = compute_collapse_metrics(e)
        assert m["effective_rank"] > 1.0

    def test_degenerate_input_is_safe(self):
        m = compute_collapse_metrics(torch.randn(1, 16))
        assert m["std_mean"] == 0.0
        assert m["effective_rank"] == 0.0


class TestEmaDrift:
    def test_identical_params_zero_drift(self):
        p = [torch.ones(4, 4), torch.zeros(3)]
        q = [torch.ones(4, 4), torch.zeros(3)]
        assert compute_ema_drift(p, q) == 0.0

    def test_drift_grows_with_divergence(self):
        p = [torch.zeros(4, 4)]
        near = compute_ema_drift(p, [torch.full((4, 4), 0.1)])
        far = compute_ema_drift(p, [torch.full((4, 4), 1.0)])
        assert far > near > 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest Programma_CS2_RENAN/tests/test_collapse_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'Programma_CS2_RENAN.backend.nn.collapse_metrics'`

- [ ] **Step 3: Write minimal implementation**

Create `Programma_CS2_RENAN/backend/nn/collapse_metrics.py`:

```python
"""Representation-collapse metrics for JEPA embeddings.

Pure functions over tensors: no TensorBoard, no model coupling, no I/O.

Collapse is the failure where the encoder emits near-constant embeddings.
The predictor then satisfies its objective trivially and the loss curve looks
healthy while nothing has been learned. These metrics detect that directly.

`effective_rank` follows RankMe (Garrido et al., 2023): the entropy-based
effective rank of the embedding matrix's singular values. Collapse drives it
toward 1 because a single direction dominates.
"""

from typing import Dict, Iterable

import torch

_EPS = 1e-12

_ZERO: Dict[str, float] = {
    "std_mean": 0.0,
    "std_min": 0.0,
    "effective_rank": 0.0,
    "cosine_offdiag_mean": 0.0,
}


def compute_collapse_metrics(embeddings: torch.Tensor) -> Dict[str, float]:
    """Return collapse indicators for an embedding matrix.

    Args:
        embeddings: tensor of shape [N, D], or any shape whose trailing
            dimension is the feature dimension (it is flattened to [-1, D]).

    Returns:
        dict with keys std_mean, std_min, effective_rank, cosine_offdiag_mean.
        All-zeros when fewer than 2 samples are available.
    """
    e = embeddings.detach().float()
    if e.dim() > 2:
        e = e.reshape(-1, e.shape[-1])
    if e.dim() != 2 or e.shape[0] < 2:
        return dict(_ZERO)

    n = e.shape[0]
    # L2-normalize so a model that merely shrinks its output magnitude is not
    # mistaken for one that collapsed in direction.
    z = torch.nn.functional.normalize(e, dim=1, eps=_EPS)

    std = z.std(dim=0)

    # RankMe effective rank on the (uncentered) normalized matrix.
    sv = torch.linalg.svdvals(z)
    p = sv / sv.sum().clamp(min=_EPS)
    entropy = -(p * torch.log(p.clamp(min=_EPS))).sum()
    effective_rank = float(torch.exp(entropy))

    sim = z @ z.T
    offdiag = (sim.sum() - torch.diagonal(sim).sum()) / (n * (n - 1))

    return {
        "std_mean": float(std.mean()),
        "std_min": float(std.min()),
        "effective_rank": effective_rank,
        "cosine_offdiag_mean": float(offdiag),
    }


def compute_ema_drift(
    online_params: Iterable[torch.Tensor],
    target_params: Iterable[torch.Tensor],
) -> float:
    """L2 distance between online and EMA-target parameter sets.

    Approaching 0 means the target encoder has stopped moving — a corroborating
    collapse signal in EMA-based JEPA training.
    """
    total = 0.0
    for p, q in zip(online_params, target_params):
        diff = p.detach().float() - q.detach().float()
        total += float(torch.sum(diff * diff))
    return float(total**0.5)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest Programma_CS2_RENAN/tests/test_collapse_metrics.py -v`
Expected: PASS — 8 tests.

- [ ] **Step 5: Commit**

```bash
git add Programma_CS2_RENAN/backend/nn/collapse_metrics.py Programma_CS2_RENAN/tests/test_collapse_metrics.py
git commit -m "feat(nn): add JEPA representation-collapse metrics"
```

---

### Task 2: Install TensorBoard and make failure loud

The feature has never run because `tensorboard` is absent and the callback degrades in silence. This task fixes both.

**Files:**
- Modify: `requirements-lock.txt`, `requirements-lock-cpu.txt`
- Modify: `Programma_CS2_RENAN/backend/nn/tensorboard_callback.py:27-33`, `:56-74`, `:78-82`
- Modify: `Programma_CS2_RENAN/tests/test_training_callbacks.py:200-240`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `TensorBoardCallback` gains attribute `writer` (already present, now guaranteed non-`None` when tensorboard is installed) and honors env var `CS2_TB_STRICT`.

- [ ] **Step 1: Install the dependency**

Add `tensorboard==2.21.0` to both lock files, immediately after the `sympy` entry (keep alphabetical grouping consistent with surrounding lines):

```
tensorboard==2.21.0
```

Then install it:

```bash
PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pip install tensorboard==2.21.0
```

Verify: `PYTHONUTF8=1 ./.venv/Scripts/python.exe -c "import tensorboard; print(tensorboard.__version__)"`
Expected: `2.21.0`

- [ ] **Step 2: Write the failing test**

Replace the body of `class TestTensorBoardCallback` in `Programma_CS2_RENAN/tests/test_training_callbacks.py` with:

```python
class TestTensorBoardCallback:
    """TensorBoard availability must be visible, never silent."""

    def test_writer_created_when_available(self):
        import tempfile

        from Programma_CS2_RENAN.backend.nn.tensorboard_callback import TensorBoardCallback

        cb = TensorBoardCallback(log_dir=tempfile.mkdtemp(prefix="test_tb_"))
        assert cb.writer is not None
        cb.close()

    def test_warns_once_when_unavailable(self, monkeypatch, caplog):
        import tempfile

        import Programma_CS2_RENAN.backend.nn.tensorboard_callback as tbmod

        monkeypatch.setattr(tbmod, "_TB_AVAILABLE", False)
        cb = tbmod.TensorBoardCallback(log_dir=tempfile.mkdtemp(prefix="test_tb_"))

        with caplog.at_level("WARNING"):
            cb.on_train_start(model=None, config={})
            cb.on_train_start(model=None, config={})

        hits = [r for r in caplog.records if "TensorBoard unavailable" in r.getMessage()]
        assert len(hits) == 1, "must warn exactly once per run"

    def test_strict_mode_raises_when_unavailable(self, monkeypatch):
        import tempfile

        import pytest

        import Programma_CS2_RENAN.backend.nn.tensorboard_callback as tbmod

        monkeypatch.setattr(tbmod, "_TB_AVAILABLE", False)
        monkeypatch.setenv("CS2_TB_STRICT", "1")

        with pytest.raises(RuntimeError, match="CS2_TB_STRICT"):
            tbmod.TensorBoardCallback(log_dir=tempfile.mkdtemp(prefix="test_tb_"))

    def test_hooks_do_not_raise_when_unavailable(self, monkeypatch):
        import tempfile

        import Programma_CS2_RENAN.backend.nn.tensorboard_callback as tbmod

        monkeypatch.setattr(tbmod, "_TB_AVAILABLE", False)
        cb = tbmod.TensorBoardCallback(log_dir=tempfile.mkdtemp(prefix="test_tb_"))
        cb.on_epoch_start(0)
        cb.on_batch_end(0, 1.0, {})
        cb.on_train_end(None, {})
        cb.close()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest Programma_CS2_RENAN/tests/test_training_callbacks.py::TestTensorBoardCallback -v`
Expected: FAIL — `test_warns_once_when_unavailable` and `test_strict_mode_raises_when_unavailable` fail (no such warning, no strict mode).

- [ ] **Step 4: Implement loud failure**

In `Programma_CS2_RENAN/backend/nn/tensorboard_callback.py`, replace the `__init__` body (currently lines 56-74) with:

```python
    def __init__(self, log_dir: Optional[str] = None, model_type: str = ""):
        self._active = _TB_AVAILABLE
        self._model_type = model_type
        self._epoch = 0
        self._global_step = 0
        self._warned_unavailable = False
        self.writer: Optional[Any] = None

        # Stage-4 relocation: default log_dir under the package's RUNS_DIR so
        # TensorBoard events co-locate with models/ instead of spawning a
        # repo-root `runs/` orphan on every train.
        if log_dir is None:
            from Programma_CS2_RENAN.core.config import RUNS_DIR

            log_dir = os.path.join(RUNS_DIR, "coach_training")

        if not self._active and os.environ.get("CS2_TB_STRICT") == "1":
            raise RuntimeError(
                "CS2_TB_STRICT=1 and tensorboard is not installed. "
                "Install it with: pip install tensorboard==2.21.0"
            )

        if self._active:
            self.writer = SummaryWriter(log_dir)
            logger.info("TensorBoard writer initialized: %s", log_dir)
```

Then replace `on_train_start` (currently lines 78-82) with:

```python
    def on_train_start(self, model, config: Dict[str, Any]) -> None:
        if not self._active or self.writer is None:
            if not self._warned_unavailable:
                self._warned_unavailable = True
                logger.warning(
                    "TensorBoard unavailable — no metrics will be recorded for "
                    "this run. Install tensorboard==2.21.0, or set "
                    "CS2_TB_STRICT=1 to fail instead of degrading."
                )
            return
        self._model_type = config.get("model_type", self._model_type)
        self._create_custom_layout()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest Programma_CS2_RENAN/tests/test_training_callbacks.py -v`
Expected: PASS — all tests in the file, including the pre-existing `TrainingCallback` and `CallbackRegistry` classes.

- [ ] **Step 6: Commit**

```bash
git add requirements-lock.txt requirements-lock-cpu.txt Programma_CS2_RENAN/backend/nn/tensorboard_callback.py Programma_CS2_RENAN/tests/test_training_callbacks.py
git commit -m "fix(nn): install tensorboard and make its absence visible"
```

---

### Task 3: Log collapse metrics from a fixed probe batch

**Files:**
- Modify: `Programma_CS2_RENAN/backend/nn/tensorboard_callback.py` (`on_train_start`, `on_epoch_end`, new private method)
- Test: `Programma_CS2_RENAN/tests/test_tensorboard_collapse_logging.py` (create)

**Interfaces:**
- Consumes: `compute_collapse_metrics`, `compute_ema_drift` from Task 1. `TensorBoardCallback._warned_unavailable` from Task 2.
- Produces: `TensorBoardCallback` reads `config["probe_batch"]` (a `dict` with key `"context"` holding a tensor) at `on_train_start`, and emits scalars tagged `embed/std_mean`, `embed/std_min`, `embed/effective_rank`, `embed/cosine_offdiag_mean`, and `embed/ema_drift`.

- [ ] **Step 1: Write the failing test**

Create `Programma_CS2_RENAN/tests/test_tensorboard_collapse_logging.py`:

```python
"""TensorBoardCallback must log collapse metrics from a fixed probe batch."""

import tempfile

import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.tensorboard_callback import TensorBoardCallback


class _StubModel(nn.Module):
    """Minimal stand-in exposing the JEPA attribute names the callback reads."""

    def __init__(self, d_in=8, d_out=16):
        super().__init__()
        self.context_encoder = nn.Linear(d_in, d_out)
        self.target_encoder = nn.Linear(d_in, d_out)


class _RecordingWriter:
    def __init__(self):
        self.scalars = {}

    def add_scalar(self, tag, value, step):
        self.scalars.setdefault(tag, []).append((step, value))

    def add_custom_scalars(self, *a, **kw):
        pass

    def add_histogram(self, *a, **kw):
        pass

    def flush(self):
        pass

    def close(self):
        pass


def _callback_with_recorder():
    cb = TensorBoardCallback(log_dir=tempfile.mkdtemp(prefix="test_tb_collapse_"))
    rec = _RecordingWriter()
    cb.writer = rec
    return cb, rec


class TestCollapseLogging:
    def test_logs_embed_scalars_each_epoch(self):
        cb, rec = _callback_with_recorder()
        model = _StubModel()
        probe = {"context": torch.randn(32, 8)}

        cb.on_train_start(model=model, config={"probe_batch": probe})
        cb.on_epoch_end(epoch=0, train_loss=1.0, val_loss=1.0, model=model)

        for tag in (
            "embed/std_mean",
            "embed/std_min",
            "embed/effective_rank",
            "embed/cosine_offdiag_mean",
            "embed/ema_drift",
        ):
            assert tag in rec.scalars, f"missing {tag}"

    def test_no_probe_batch_skips_without_raising(self):
        cb, rec = _callback_with_recorder()
        model = _StubModel()

        cb.on_train_start(model=model, config={})
        cb.on_epoch_end(epoch=0, train_loss=1.0, val_loss=1.0, model=model)

        assert not any(t.startswith("embed/") for t in rec.scalars)

    def test_probe_batch_is_fixed_across_epochs(self):
        cb, rec = _callback_with_recorder()
        model = _StubModel()
        probe = {"context": torch.randn(32, 8)}

        cb.on_train_start(model=model, config={"probe_batch": probe})
        cb.on_epoch_end(epoch=0, train_loss=1.0, val_loss=1.0, model=model)
        cb.on_epoch_end(epoch=1, train_loss=1.0, val_loss=1.0, model=model)

        # Model never trained between epochs, so a fixed probe must give
        # identical values. A varying batch would not.
        vals = [v for _, v in rec.scalars["embed/std_mean"]]
        assert abs(vals[0] - vals[1]) < 1e-6

    def test_model_without_encoders_is_skipped(self):
        cb, rec = _callback_with_recorder()
        model = nn.Linear(4, 4)  # no context_encoder attribute

        cb.on_train_start(model=model, config={"probe_batch": {"context": torch.randn(8, 4)}})
        cb.on_epoch_end(epoch=0, train_loss=1.0, val_loss=1.0, model=model)

        assert not any(t.startswith("embed/") for t in rec.scalars)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest Programma_CS2_RENAN/tests/test_tensorboard_collapse_logging.py -v`
Expected: FAIL — `test_logs_embed_scalars_each_epoch` fails with `missing embed/std_mean`.

- [ ] **Step 3: Capture the probe batch**

In `on_train_start` (as rewritten in Task 2), add probe capture immediately before `self._create_custom_layout()`:

```python
        self._model_type = config.get("model_type", self._model_type)
        self._probe_batch = config.get("probe_batch")
        if self._probe_batch is None:
            logger.warning(
                "No probe_batch supplied — collapse metrics (embed/*) will not "
                "be logged for this run."
            )
        self._create_custom_layout()
```

And initialize it in `__init__`, next to `self._warned_unavailable`:

```python
        self._probe_batch: Optional[Any] = None
```

- [ ] **Step 4: Implement metric logging**

Add this private method to `TensorBoardCallback`, directly above `_log_parameter_histograms`:

```python
    def _log_collapse_metrics(self, model, epoch: int) -> None:
        """Log representation-collapse indicators from the fixed probe batch."""
        if self.writer is None or self._probe_batch is None:
            return

        encoder = getattr(model, "context_encoder", None)
        if encoder is None:
            return

        context = self._probe_batch.get("context")
        if context is None:
            return

        from Programma_CS2_RENAN.backend.nn.collapse_metrics import (
            compute_collapse_metrics,
            compute_ema_drift,
        )

        with torch.no_grad():
            try:
                device = next(model.parameters()).device
            except StopIteration:
                device = torch.device("cpu")
            embeddings = encoder(context.to(device))

        for name, value in compute_collapse_metrics(embeddings).items():
            self.writer.add_scalar(f"embed/{name}", value, epoch)

        target = getattr(model, "target_encoder", None)
        if target is not None:
            self.writer.add_scalar(
                "embed/ema_drift",
                compute_ema_drift(encoder.parameters(), target.parameters()),
                epoch,
            )
```

Then call it from `on_epoch_end`, immediately before `self._log_parameter_histograms(model, epoch)`:

```python
        self._log_collapse_metrics(model, epoch)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest Programma_CS2_RENAN/tests/test_tensorboard_collapse_logging.py -v`
Expected: PASS — 4 tests.

- [ ] **Step 6: Commit**

```bash
git add Programma_CS2_RENAN/backend/nn/tensorboard_callback.py Programma_CS2_RENAN/tests/test_tensorboard_collapse_logging.py
git commit -m "feat(nn): log JEPA collapse metrics from a fixed probe batch"
```

---

### Task 4: Run-scoped log directory with device tag

Prevents a Windows CPU smoke run from being mistaken for a Linux ROCm run in the dashboard.

**Files:**
- Modify: `Programma_CS2_RENAN/backend/nn/tensorboard_callback.py` (module-level helpers)
- Test: `Programma_CS2_RENAN/tests/test_tensorboard_run_layout.py` (create)

**Interfaces:**
- Consumes: nothing from Tasks 1-3.
- Produces: module-level `resolve_device_tag() -> str` and `build_run_dir(model_type: str) -> str` in `tensorboard_callback.py`.

- [ ] **Step 1: Write the failing test**

Create `Programma_CS2_RENAN/tests/test_tensorboard_run_layout.py`:

```python
"""Run directories must be unique per run and name the device actually used."""

import os
import re

from Programma_CS2_RENAN.backend.nn.tensorboard_callback import (
    build_run_dir,
    resolve_device_tag,
)


class TestDeviceTag:
    def test_returns_known_tag(self):
        assert resolve_device_tag() in {"cpu", "cuda", "rocm"}

    def test_cpu_when_no_gpu(self, monkeypatch):
        import torch

        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
        assert resolve_device_tag() == "cpu"


class TestRunDir:
    def test_contains_model_type_and_device(self):
        d = build_run_dir("jepa_pretrain")
        assert "jepa_pretrain" in d
        assert resolve_device_tag() in os.path.basename(d)

    def test_run_id_is_utc_timestamped(self):
        run_id = os.path.basename(build_run_dir("jepa_pretrain"))
        assert re.match(r"^\d{8}T\d{6}Z-(cpu|cuda|rocm)$", run_id), run_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest Programma_CS2_RENAN/tests/test_tensorboard_run_layout.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_run_dir'`

- [ ] **Step 3: Implement the helpers**

Add to `Programma_CS2_RENAN/backend/nn/tensorboard_callback.py`, directly after the `logger = get_logger(...)` line:

```python
from datetime import datetime, timezone


def resolve_device_tag() -> str:
    """Name the accelerator training actually ran on, not the one requested."""
    if not torch.cuda.is_available():
        return "cpu"
    if getattr(torch.version, "hip", None):
        return "rocm"
    if getattr(torch.version, "cuda", None):
        return "cuda"
    return "cpu"


def build_run_dir(model_type: str) -> str:
    """Return RUNS_DIR/<model_type>/<UTC timestamp>-<device tag>."""
    from Programma_CS2_RENAN.core.config import RUNS_DIR

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return os.path.join(RUNS_DIR, model_type, f"{stamp}-{resolve_device_tag()}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest Programma_CS2_RENAN/tests/test_tensorboard_run_layout.py -v`
Expected: PASS — 4 tests.

- [ ] **Step 5: Commit**

```bash
git add Programma_CS2_RENAN/backend/nn/tensorboard_callback.py Programma_CS2_RENAN/tests/test_tensorboard_run_layout.py
git commit -m "feat(nn): run-scoped tensorboard log dirs tagged by device"
```

---

### Task 5: Wire the projector into JEPA training on a shared writer

This is the fragmentation fix and the point where the orphaned `EmbeddingProjector` finally runs.

**Files:**
- Modify: `Programma_CS2_RENAN/backend/nn/jepa_train.py:444` (signature default), `:455-456` (callback construction), `:476-486` (probe batch into config)
- Test: `Programma_CS2_RENAN/tests/test_tensorboard_integration.py` (create)

**Interfaces:**
- Consumes: `build_run_dir` (Task 4), `TensorBoardCallback` with `writer` and probe-batch support (Tasks 2-3).
- Produces: `pretrain_jepa(...)` registers `[TensorBoardCallback, EmbeddingProjector]` sharing one writer, and supplies `config["probe_batch"]`.

- [ ] **Step 1: Write the failing test**

Create `Programma_CS2_RENAN/tests/test_tensorboard_integration.py`:

```python
"""One writer per run: exactly one event file, containing embed/* tags."""

import tempfile
from pathlib import Path

import pytest
import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.embedding_projector import EmbeddingProjector
from Programma_CS2_RENAN.backend.nn.tensorboard_callback import TensorBoardCallback
from Programma_CS2_RENAN.backend.nn.training_callbacks import CallbackRegistry


class _StubModel(nn.Module):
    def __init__(self, d_in=8, d_out=16):
        super().__init__()
        self.context_encoder = nn.Linear(d_in, d_out)
        self.target_encoder = nn.Linear(d_in, d_out)


def test_shared_writer_produces_single_event_file():
    log_dir = tempfile.mkdtemp(prefix="test_tb_integration_")
    tb = TensorBoardCallback(log_dir=log_dir, model_type="jepa_pretrain")
    projector = EmbeddingProjector(tb_writer=tb.writer, interval=1)
    callbacks = CallbackRegistry([tb, projector])

    model = _StubModel()
    probe = {"context": torch.randn(16, 8)}

    callbacks.fire(
        "on_train_start",
        model=model,
        config={"model_type": "jepa_pretrain", "probe_batch": probe},
    )
    for epoch in range(2):
        callbacks.fire(
            "on_epoch_end",
            epoch=epoch,
            train_loss=1.0,
            val_loss=1.0,
            model=model,
        )
    callbacks.close_all()

    events = list(Path(log_dir).glob("events.out.tfevents.*"))
    assert len(events) == 1, f"expected 1 event file, found {len(events)}: {events}"


def test_event_file_contains_collapse_tags():
    ea = pytest.importorskip(
        "tensorboard.backend.event_processing.event_accumulator"
    )

    log_dir = tempfile.mkdtemp(prefix="test_tb_tags_")
    tb = TensorBoardCallback(log_dir=log_dir, model_type="jepa_pretrain")
    callbacks = CallbackRegistry([tb])

    model = _StubModel()
    callbacks.fire(
        "on_train_start",
        model=model,
        config={"model_type": "jepa_pretrain", "probe_batch": {"context": torch.randn(16, 8)}},
    )
    callbacks.fire("on_epoch_end", epoch=0, train_loss=1.0, val_loss=1.0, model=model)
    callbacks.close_all()

    acc = ea.EventAccumulator(log_dir)
    acc.Reload()
    tags = set(acc.Tags()["scalars"])
    assert "embed/std_mean" in tags
    assert "embed/effective_rank" in tags
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest Programma_CS2_RENAN/tests/test_tensorboard_integration.py -v`
Expected: FAIL — either more than one event file, or `embed/*` tags absent.

Note: if `test_shared_writer_produces_single_event_file` already passes at this point, that is meaningful information — it means the historical 8-file fragmentation came from repeated `TensorBoardCallback` construction elsewhere rather than from the projector. Record that finding and continue; the test still guards the invariant.

- [ ] **Step 3: Wire the projector and probe batch in `jepa_train.py`**

Replace lines 455-456 with:

```python
    tb_callback = TensorBoardCallback(log_dir=log_dir, model_type="jepa_pretrain")
    from Programma_CS2_RENAN.backend.nn.embedding_projector import EmbeddingProjector

    projector = EmbeddingProjector(tb_writer=tb_callback.writer, interval=5)
    callbacks = CallbackRegistry([tb_callback, projector])
```

Change the `log_dir` default at line 444 from `"runs/jepa_pretrain"` to `None`, and resolve it right before constructing the callback:

```python
    if log_dir is None:
        from Programma_CS2_RENAN.backend.nn.tensorboard_callback import build_run_dir

        log_dir = build_run_dir("jepa_pretrain")
```

Then add the probe batch to `train_config` (inserted into the dict literal at lines 476-485, after `"device": str(device),`):

```python
        "probe_batch": next(iter(dataloader)),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest Programma_CS2_RENAN/tests/test_tensorboard_integration.py -v`
Expected: PASS — 2 tests.

- [ ] **Step 5: Run the full NN test suite for regressions**

Run: `PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest Programma_CS2_RENAN/tests/ -v -k "callback or jepa or collapse or tensorboard"`
Expected: PASS. `test_jepa_training_pipeline.py` is the one most likely to notice the `train_config` and `log_dir` changes — if it fails, the wiring altered behavior it asserts, and the fix belongs here rather than in the test.

- [ ] **Step 6: Commit**

```bash
git add Programma_CS2_RENAN/backend/nn/jepa_train.py Programma_CS2_RENAN/tests/test_tensorboard_integration.py
git commit -m "feat(nn): wire embedding projector onto shared tensorboard writer"
```

---

## Verifying the Result

After Task 5, launch the dashboard against the run root:

```bash
PYTHONUTF8=1 ./.venv/Scripts/python.exe -m tensorboard.main --logdir Programma_CS2_RENAN/runs
```

Open `http://localhost:6006`. On a real (Linux/ROCm) training run you are looking for:

- `embed/effective_rank` trending toward **1** — collapse. Healthy training holds it well above 1.
- `embed/cosine_offdiag_mean` climbing toward **1** — collapse.
- `embed/std_mean` decaying toward **0** — collapse.
- `embed/ema_drift` flatlining at **0** — the target encoder has stopped moving.

A falling `jepa/infonce_loss` alongside any of those means the loss is being satisfied trivially. That combination is the whole reason this instrument exists.

The PROJECTOR tab shows the concept/belief embeddings written every 5 epochs; healthy structure appears as separable clusters rather than one undifferentiated blob.
