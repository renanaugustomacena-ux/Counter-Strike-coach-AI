"""Unit tests for the PRE-6 concept_temperature saturation alarm.

Per CS2_Coach_Modernization_Report.pdf §8.3, the VL-JEPA concept_temperature
parameter is a learned scalar clamped to [0.01, 1.0]. If at convergence it
saturates against either boundary, the concept space is degenerate (binary
collapse at 0.01 or uniform / non-discriminative at 1.0). The observatory
must detect this after 10 consecutive saturated epochs and emit a one-shot
WARN_CONCEPT_TEMPERATURE_SATURATED event.

These tests construct a minimal stand-in model exposing only the field the
observatory reads (``concept_temperature``) — no JEPA encoder, no DB, no
DataLoader. on_epoch_end is invoked directly with synthetic temperatures.
"""

import torch
from torch import nn

from Programma_CS2_RENAN.backend.nn.maturity_observatory import (
    CONCEPT_TEMP_SATURATION_PATIENCE,
    MaturityObservatory,
)


class _MockVLModel(nn.Module):
    """Minimal stand-in: only the fields the observatory reads."""

    def __init__(self, temperature: float):
        super().__init__()
        self.concept_temperature = nn.Parameter(torch.tensor(float(temperature)))

    # The observatory's other compute_* helpers tolerate missing attributes —
    # they short-circuit on getattr returning None. Nothing else needed here.


def _drive_epoch(obs: MaturityObservatory, epoch: int, temp: float) -> None:
    """Drive one on_epoch_end with a frozen temperature value."""
    obs.on_epoch_end(epoch=epoch, train_loss=0.5, val_loss=0.5, model=_MockVLModel(temp))


def test_healthy_temperature_never_alarms():
    """Mid-band temperatures never trigger the saturation warning."""
    obs = MaturityObservatory()
    for epoch in range(20):
        _drive_epoch(obs, epoch, temp=0.5)  # squarely in the middle
    snap = obs.history[-1]
    assert snap.concept_temperature_saturated is False
    assert snap.concept_temperature_saturation_warning is False


def test_lower_saturation_at_0_011_alarms_after_10_epochs():
    """The PRE-6 DoD: temp=0.011 frozen for 10 epochs must raise the alarm."""
    obs = MaturityObservatory()
    for epoch in range(CONCEPT_TEMP_SATURATION_PATIENCE):
        _drive_epoch(obs, epoch, temp=0.011)
    snap = obs.history[-1]
    assert snap.concept_temperature == pytest_approx(0.011)
    assert snap.concept_temperature_saturated is True
    assert snap.concept_temperature_saturation_warning is True


def test_lower_saturation_at_9_epochs_does_not_alarm():
    """Patience-1 saturated epochs is not enough."""
    obs = MaturityObservatory()
    for epoch in range(CONCEPT_TEMP_SATURATION_PATIENCE - 1):
        _drive_epoch(obs, epoch, temp=0.011)
    snap = obs.history[-1]
    assert snap.concept_temperature_saturated is True
    assert snap.concept_temperature_saturation_warning is False


def test_upper_saturation_alarms():
    """Saturating against the upper boundary (uniform/non-discriminative)
    must also alarm — symmetrically with the lower case."""
    obs = MaturityObservatory()
    for epoch in range(CONCEPT_TEMP_SATURATION_PATIENCE):
        _drive_epoch(obs, epoch, temp=0.99)
    snap = obs.history[-1]
    assert snap.concept_temperature == pytest_approx(0.99)
    assert snap.concept_temperature_saturated is True
    assert snap.concept_temperature_saturation_warning is True


def test_recovery_resets_saturation_streak():
    """A single healthy epoch breaks the streak."""
    obs = MaturityObservatory()
    # 9 saturated epochs (just under patience).
    for epoch in range(CONCEPT_TEMP_SATURATION_PATIENCE - 1):
        _drive_epoch(obs, epoch, temp=0.011)
    # One healthy recovery — resets the streak.
    _drive_epoch(obs, CONCEPT_TEMP_SATURATION_PATIENCE - 1, temp=0.5)
    # Now another 9 saturated — still under patience because the streak reset.
    for offset in range(CONCEPT_TEMP_SATURATION_PATIENCE - 1):
        _drive_epoch(obs, CONCEPT_TEMP_SATURATION_PATIENCE + offset, temp=0.011)
    snap = obs.history[-1]
    assert snap.concept_temperature_saturated is True
    assert snap.concept_temperature_saturation_warning is False


def test_model_without_concept_temperature_no_alarm():
    """Non-VL models (no concept_temperature attr) must not crash or alarm."""

    class _Empty(nn.Module):
        pass

    obs = MaturityObservatory()
    obs.on_epoch_end(epoch=0, train_loss=0.5, val_loss=0.5, model=_Empty())
    snap = obs.history[-1]
    # Defaults preserved — None temperature, both flags False.
    assert snap.concept_temperature is None
    assert snap.concept_temperature_saturated is False
    assert snap.concept_temperature_saturation_warning is False


def test_alarm_latch_does_not_spam_logs():
    """Once the warning fires, additional saturated epochs do NOT re-emit
    the WARN_CONCEPT_TEMPERATURE_SATURATED log entry.

    The project loggers run with ``propagate=False`` (logger_setup.py:208),
    so pytest's caplog cannot intercept them via the root logger. We
    instead verify the property the log line is gated on:
    ``_concept_temp_warning_logged`` flips True on first emission and
    stays True until a healthy epoch breaks the streak. Each subsequent
    saturated epoch checks this latch and short-circuits before logging.
    """
    obs = MaturityObservatory()
    # Run to threshold + a few extras.
    for epoch in range(CONCEPT_TEMP_SATURATION_PATIENCE + 5):
        _drive_epoch(obs, epoch, temp=0.011)

    # Latch is locked → subsequent epochs would not re-emit.
    assert obs._concept_temp_warning_logged is True
    # Snapshot flag stays True throughout the saturated run.
    for snap in obs.history[CONCEPT_TEMP_SATURATION_PATIENCE - 1 :]:
        assert snap.concept_temperature_saturation_warning is True

    # A recovery epoch resets the latch so a NEW saturation episode
    # would emit again.
    _drive_epoch(obs, CONCEPT_TEMP_SATURATION_PATIENCE + 5, temp=0.5)
    assert obs._concept_temp_warning_logged is False
    assert obs._concept_temp_saturation_streak == 0


# Local helper to avoid pytest.approx in lots of asserts.
def pytest_approx(expected, rel=1e-6):
    import pytest

    return pytest.approx(expected, rel=rel)
