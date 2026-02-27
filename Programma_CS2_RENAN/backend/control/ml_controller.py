import threading
import time
from typing import Dict, Optional

from Programma_CS2_RENAN.backend.storage.state_manager import state_manager
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.ml_controller")


class MLControlContext:
    """
    Control token passed to ML loops to allow real-time intervention.
    """

    def __init__(self):
        self._stop_requested = False
        self._pause_requested = False
        self._throttle_factor = 0.0  # 0.0 = full speed, 1.0 = maximum delay
        self._lock = threading.Lock()

    def check_state(self):
        """Called by training loops to respect operator commands."""
        while self._pause_requested:
            time.sleep(1)

        if self._stop_requested:
            raise StopIteration("ML Operator requested termination.")

        if self._throttle_factor > 0:
            time.sleep(self._throttle_factor)

    @property
    def stop_requested(self):
        return self._stop_requested

    @property
    def pause_requested(self):
        return self._pause_requested

    def request_stop(self):
        self._stop_requested = True

    def request_pause(self):
        self._pause_requested = True

    def request_resume(self):
        self._pause_requested = False

    def set_throttle(self, value: float):
        self._throttle_factor = value


class MLController:
    """
    Supervisor for the Machine Learning lifecycle.
    """

    def __init__(self):
        self.context = MLControlContext()
        self.thread: Optional[threading.Thread] = None
        self._is_running = False

    def start_training(self):
        """Launches the training cycle in a managed thread."""
        if self._is_running:
            logger.warning("MLController: Training already in progress.")
            return

        self._is_running = True
        self.context._stop_requested = False
        self.thread = threading.Thread(target=self._run_wrapper, daemon=True)
        self.thread.start()

    def stop_training(self):
        """Signals the ML stack to terminate at the next safe checkpoint."""
        logger.info("MLController: Requesting soft-stop...")
        self.context.request_stop()

    def pause_training(self):
        self.context.request_pause()
        state_manager.update_status("teacher", "Paused", "Training suspended by operator.")

    def resume_training(self):
        self.context.request_resume()
        state_manager.update_status("teacher", "Running", "Resuming training cycle...")

    def _run_wrapper(self):
        from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager

        try:
            manager = CoachTrainingManager()
            # We will refactor run_full_cycle to accept context
            manager.run_full_cycle(context=self.context)
        except StopIteration:
            logger.info("MLController: Training stopped gracefully by operator.")
            state_manager.update_status("teacher", "Stopped", "Manually terminated.")
        except Exception as e:
            logger.error("MLController: Training cycle crashed: %s", e)
            state_manager.set_error("teacher", str(e))
        finally:
            self._is_running = False
            self.thread = None

    def get_status(self) -> Dict:
        return {
            "is_running": self._is_running,
            "paused": self.context.pause_requested,
            "stop_requested": self.context.stop_requested,
        }
