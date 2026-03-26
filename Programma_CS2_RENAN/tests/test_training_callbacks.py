"""
Comprehensive CI tests for training callbacks framework.

Covers: TrainingCallback, CallbackRegistry (dispatch, error isolation,
duplicate prevention), and TensorBoardCallback (graceful no-op when
tensorboard is not installed).

Target: 100% coverage of training_callbacks.py + tensorboard_callback.py.
"""

import tempfile
from unittest.mock import MagicMock, patch

import pytest
import torch

from Programma_CS2_RENAN.backend.nn.training_callbacks import (
    CallbackRegistry,
    TrainingCallback,
)


# ─── TrainingCallback (Abstract Base) ─────────────────────────────────


class TestTrainingCallback:
    """Verify the opt-in pattern: all hooks are no-ops by default."""

    def test_all_hooks_are_no_ops(self):
        """Calling any hook on the base class should not raise."""

        class ConcreteCallback(TrainingCallback):
            pass

        cb = ConcreteCallback()
        cb.on_train_start(model=None, config={})
        cb.on_epoch_start(epoch=1)
        cb.on_batch_end(batch_idx=0, loss=0.5, outputs={})
        cb.on_epoch_end(epoch=1, train_loss=0.1, val_loss=0.2, model=None)
        cb.on_validation_end(epoch=1, val_loss=0.2, model=None)
        cb.on_train_end(model=None, final_metrics={})
        cb.close()

    def test_subclass_can_override_individual_hooks(self):
        """Subclass should be able to override just the hooks it needs."""
        called = []

        class MyCallback(TrainingCallback):
            def on_epoch_end(self, epoch, train_loss, val_loss, model, **kwargs):
                called.append(epoch)

        cb = MyCallback()
        cb.on_epoch_end(epoch=5, train_loss=0.1, val_loss=0.2, model=None)
        assert called == [5]


# ─── CallbackRegistry ─────────────────────────────────────────────────


class TestCallbackRegistry:
    def test_init_empty(self):
        reg = CallbackRegistry()
        assert len(reg.callbacks) == 0

    def test_init_with_callbacks(self):
        cb1 = TrainingCallback()
        cb2 = TrainingCallback()
        reg = CallbackRegistry([cb1, cb2])
        assert len(reg.callbacks) == 2

    def test_add_callback(self):
        reg = CallbackRegistry()

        class MyCallback(TrainingCallback):
            pass

        cb = MyCallback()
        reg.add(cb)
        assert len(reg.callbacks) == 1
        assert reg.callbacks[0] is cb

    def test_add_duplicate_prevented(self):
        """NN-L-13: Same callback instance should not be added twice."""
        reg = CallbackRegistry()

        class MyCallback(TrainingCallback):
            pass

        cb = MyCallback()
        reg.add(cb)
        reg.add(cb)  # duplicate
        assert len(reg.callbacks) == 1

    def test_add_different_instances_allowed(self):
        """Different instances of the same class should both be registered."""
        reg = CallbackRegistry()

        class MyCallback(TrainingCallback):
            pass

        reg.add(MyCallback())
        reg.add(MyCallback())
        assert len(reg.callbacks) == 2


class TestCallbackRegistryFire:
    def test_fire_dispatches_to_all(self):
        results = []

        class CB1(TrainingCallback):
            def on_epoch_start(self, epoch):
                results.append(("cb1", epoch))

        class CB2(TrainingCallback):
            def on_epoch_start(self, epoch):
                results.append(("cb2", epoch))

        reg = CallbackRegistry([CB1(), CB2()])
        reg.fire("on_epoch_start", epoch=3)
        assert ("cb1", 3) in results
        assert ("cb2", 3) in results

    def test_fire_unknown_event_is_noop(self):
        """Firing an event that no callback implements should not crash."""
        reg = CallbackRegistry([TrainingCallback()])
        # Should not raise
        reg.fire("on_nonexistent_event", foo=42)

    def test_fire_error_isolation(self):
        """Errors in one callback should not prevent others from running."""
        results = []

        class BadCallback(TrainingCallback):
            def on_epoch_start(self, epoch):
                raise ValueError("Intentional error")

        class GoodCallback(TrainingCallback):
            def on_epoch_start(self, epoch):
                results.append(epoch)

        reg = CallbackRegistry([BadCallback(), GoodCallback()])
        # Should not raise — BadCallback error is caught and logged
        reg.fire("on_epoch_start", epoch=1)
        assert 1 in results, "GoodCallback should still execute after BadCallback fails"

    def test_fire_passes_kwargs(self):
        received = {}

        class CapturingCallback(TrainingCallback):
            def on_epoch_end(self, epoch, train_loss, val_loss, model, **kwargs):
                received["epoch"] = epoch
                received["train_loss"] = train_loss
                received["val_loss"] = val_loss
                received.update(kwargs)

        reg = CallbackRegistry([CapturingCallback()])
        reg.fire(
            "on_epoch_end",
            epoch=5,
            train_loss=0.1,
            val_loss=0.2,
            model=None,
            optimizer="adam",
        )
        assert received["epoch"] == 5
        assert received["train_loss"] == 0.1
        assert received["optimizer"] == "adam"

    def test_fire_empty_registry_is_noop(self):
        """No callbacks registered — fire should be a no-op."""
        reg = CallbackRegistry()
        reg.fire("on_train_start", model=None, config={})
        # No error


class TestCallbackRegistryCloseAll:
    def test_close_all_calls_close_on_each(self):
        close_count = [0]

        class ClosingCallback(TrainingCallback):
            def close(self):
                close_count[0] += 1

        reg = CallbackRegistry([ClosingCallback(), ClosingCallback()])
        reg.close_all()
        assert close_count[0] == 2

    def test_close_all_error_isolation(self):
        """Errors in close() should not prevent other callbacks from closing."""
        closed = []

        class BadClose(TrainingCallback):
            def close(self):
                raise RuntimeError("close error")

        class GoodClose(TrainingCallback):
            def close(self):
                closed.append(True)

        reg = CallbackRegistry([BadClose(), GoodClose()])
        reg.close_all()
        assert len(closed) == 1


# ─── TensorBoardCallback ──────────────────────────────────────────────


class TestTensorBoardCallback:
    """Test TensorBoardCallback graceful behavior when tensorboard is NOT installed."""

    def test_import_without_tensorboard(self):
        """Module should import even without tensorboard package."""
        from Programma_CS2_RENAN.backend.nn.tensorboard_callback import (
            TensorBoardCallback,
        )

        assert TensorBoardCallback is not None

    def test_noop_when_tensorboard_missing(self):
        """All hooks should be no-ops when tensorboard is not installed."""
        from Programma_CS2_RENAN.backend.nn.tensorboard_callback import (
            TensorBoardCallback,
            _TB_AVAILABLE,
        )

        cb = TensorBoardCallback(log_dir=tempfile.mkdtemp(prefix="test_tb_"))
        # These should not raise even without tensorboard
        if not _TB_AVAILABLE:
            cb.on_train_start(model=None, config={})
            cb.on_epoch_start(epoch=0)
            cb.on_batch_end(batch_idx=0, loss=0.5, outputs={})
            cb.on_epoch_end(epoch=0, train_loss=0.1, val_loss=0.2, model=None)
            cb.on_train_end(model=None, final_metrics={"loss": 0.1})
            cb.close()

    def test_active_flag_matches_availability(self):
        """_active should match _TB_AVAILABLE."""
        from Programma_CS2_RENAN.backend.nn.tensorboard_callback import (
            TensorBoardCallback,
            _TB_AVAILABLE,
        )

        cb = TensorBoardCallback(log_dir=tempfile.mkdtemp(prefix="test_tb_"))
        assert cb._active == _TB_AVAILABLE

    def test_callback_integrates_with_registry(self):
        """TensorBoardCallback should work in CallbackRegistry without errors."""
        from Programma_CS2_RENAN.backend.nn.tensorboard_callback import (
            TensorBoardCallback,
        )

        cb = TensorBoardCallback(log_dir=tempfile.mkdtemp(prefix="test_tb_reg_"))
        reg = CallbackRegistry([cb])
        reg.fire("on_train_start", model=None, config={})
        reg.fire("on_epoch_start", epoch=0)
        reg.fire(
            "on_batch_end",
            batch_idx=0,
            loss=0.5,
            outputs={"infonce_loss": 0.3},
        )
        reg.fire(
            "on_epoch_end",
            epoch=0,
            train_loss=0.1,
            val_loss=0.2,
            model=None,
        )
        reg.close_all()
