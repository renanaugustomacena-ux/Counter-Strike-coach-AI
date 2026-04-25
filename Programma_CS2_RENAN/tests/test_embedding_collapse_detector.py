"""Unit tests for EmbeddingCollapseDetector — the P9-02 hard-stop guard.

Per CS2_Coach_Modernization_Report.pdf §9 (Logical Coherence Audit) and
the N=260 supplement §5.1 item 4: embedding variance below 0.01 across
two consecutive validation epochs must abort training. This file exercises
that gate in isolation — no JEPA model, no DataLoader, no DB connection.

The test injects synthetic per-epoch variance values directly into
EmbeddingCollapseDetector.update() and asserts the abort behaviour.
"""

import math

import pytest

from Programma_CS2_RENAN.backend.nn.early_stopping import (
    EmbeddingCollapseDetector,
    EmbeddingCollapseError,
)


def test_healthy_variances_never_raise():
    """A run with consistently healthy variance must never abort."""
    d = EmbeddingCollapseDetector(threshold=0.01, patience=2)
    for _ in range(20):
        d.update(0.05)  # well above threshold
    assert d.consecutive_collapsed == 0


def test_single_collapsed_epoch_does_not_raise():
    """One bad epoch must NOT abort — patience=2 requires two in a row."""
    d = EmbeddingCollapseDetector(threshold=0.01, patience=2)
    d.update(0.001)  # below threshold
    assert d.consecutive_collapsed == 1
    # Recovery before the second strike resets the counter
    d.update(0.05)
    assert d.consecutive_collapsed == 0


def test_two_consecutive_collapsed_epochs_abort():
    """Two bad epochs back-to-back must raise EmbeddingCollapseError."""
    d = EmbeddingCollapseDetector(threshold=0.01, patience=2)
    d.update(0.001)  # strike 1
    with pytest.raises(EmbeddingCollapseError) as excinfo:
        d.update(0.0005)  # strike 2 — abort
    msg = str(excinfo.value)
    assert "P9-02" in msg
    assert "consecutive epochs" in msg


def test_recovery_then_collapse_resets_counter():
    """A healthy epoch between two bad ones must NOT trigger abort."""
    d = EmbeddingCollapseDetector(threshold=0.01, patience=2)
    d.update(0.001)  # strike 1
    d.update(0.05)  # recovery — counter back to 0
    d.update(0.001)  # strike 1 again, NOT 2
    # No raise expected; we are at 1 of 2.
    assert d.consecutive_collapsed == 1


def test_at_threshold_is_healthy():
    """A variance EQUAL to the threshold is considered healthy (>= threshold)."""
    d = EmbeddingCollapseDetector(threshold=0.01, patience=2)
    d.update(0.01)
    assert d.consecutive_collapsed == 0


def test_nan_variance_treated_as_collapse():
    """NaN should fail closed — count it as collapse, not as healthy."""
    d = EmbeddingCollapseDetector(threshold=0.01, patience=2)
    d.update(math.nan)
    assert d.consecutive_collapsed == 1
    with pytest.raises(EmbeddingCollapseError):
        d.update(math.nan)


def test_negative_variance_treated_as_collapse():
    """Negative variance is mathematically impossible but defensively
    treated as collapse (caller bug or numerical underflow)."""
    d = EmbeddingCollapseDetector(threshold=0.01, patience=2)
    d.update(-1e-9)  # strike 1
    with pytest.raises(EmbeddingCollapseError):
        d.update(-1e-9)  # strike 2 — abort


def test_reset_clears_state():
    """reset() must zero the counter so retraining can proceed."""
    d = EmbeddingCollapseDetector(threshold=0.01, patience=2)
    d.update(0.001)
    assert d.consecutive_collapsed == 1
    d.reset()
    assert d.consecutive_collapsed == 0
    # After reset, single strike should not raise.
    d.update(0.001)
    assert d.consecutive_collapsed == 1


def test_custom_patience_three_takes_three_strikes():
    """Patience parameter must control the number of strikes needed."""
    d = EmbeddingCollapseDetector(threshold=0.01, patience=3)
    d.update(0.001)
    d.update(0.001)
    # Two strikes — patience=3, so still alive
    with pytest.raises(EmbeddingCollapseError):
        d.update(0.001)


def test_error_message_includes_diagnostic_hints():
    """The raised error must include actionable hints, per the docstring."""
    d = EmbeddingCollapseDetector(threshold=0.01, patience=2)
    d.update(0.001)
    with pytest.raises(EmbeddingCollapseError) as excinfo:
        d.update(0.001)
    msg = str(excinfo.value)
    # Cover the diagnostic categories: τ, EMA, data, VICReg.
    for hint in ("InfoNCE", "EMA", "VICReg", "data"):
        assert hint in msg, f"expected hint '{hint}' in error message:\n{msg}"
