import logging
import os
import time
from collections import deque
from threading import Lock

import psutil

logger = logging.getLogger("cs2analyzer.resource_manager")

# CPU usage smoothing configuration
_CPU_SAMPLE_WINDOW = 10  # seconds of history to maintain
_CPU_SAMPLE_COUNT = 10  # number of samples in window
_cpu_samples = deque(maxlen=_CPU_SAMPLE_COUNT)
_cpu_sample_lock = Lock()
_last_cpu_sample_time = 0

# Hysteresis thresholds to prevent rapid toggling
_THROTTLE_HIGH_THRESHOLD = 85  # Start throttling above this
_THROTTLE_LOW_THRESHOLD = 70  # Stop throttling below this
_current_throttle_state = False
# F6-18: Separate lock for throttle state — _cpu_sample_lock guards CPU samples only.
_throttle_lock = Lock()


class ResourceManager:
    """
    Governs system resource usage for background tasks.
    Ensures the 'Digester' daemon doesn't impact user experience.
    Uses a 10-second moving average with hysteresis to prevent toggle thrashing.
    """

    @staticmethod
    def _sample_cpu():
        """Non-blocking CPU sample collection."""
        global _last_cpu_sample_time

        current_time = time.time()
        sample_interval = _CPU_SAMPLE_WINDOW / _CPU_SAMPLE_COUNT

        with _cpu_sample_lock:
            # Only sample if enough time has passed
            if current_time - _last_cpu_sample_time >= sample_interval:
                # Non-blocking call (interval=None uses cached value)
                cpu = psutil.cpu_percent(interval=None)
                _cpu_samples.append(cpu)
                _last_cpu_sample_time = current_time

    @staticmethod
    def get_system_stats():
        """Returns system stats with smoothed CPU value."""
        ResourceManager._sample_cpu()

        with _cpu_sample_lock:
            if _cpu_samples:
                avg_cpu = sum(_cpu_samples) / len(_cpu_samples)
            else:
                # Bootstrap: get a quick sample if no history
                avg_cpu = psutil.cpu_percent(interval=0.05)

        return {
            "cpu": avg_cpu,
            "cpu_instant": psutil.cpu_percent(interval=None),
            "ram": psutil.virtual_memory().percent,
        }

    @staticmethod
    def should_throttle():
        """
        Determines if background tasks should slow down.
        Uses hysteresis to prevent rapid toggle thrashing.
        """
        global _current_throttle_state

        # In HP mode (Turbo), we never throttle.
        hp_mode = os.environ.get("HP_MODE", "0") == "1"
        if hp_mode:
            with _throttle_lock:  # F6-18: thread-safe write
                _current_throttle_state = False
            return False

        stats = ResourceManager.get_system_stats()
        cpu = stats["cpu"]
        ram = stats["ram"]

        # RAM check is immediate (no hysteresis needed)
        if ram > 90:
            with _throttle_lock:  # F6-18: thread-safe write
                _current_throttle_state = True
            return True

        # CPU check with hysteresis — F6-18: protect read-modify-write under lock
        with _throttle_lock:
            if _current_throttle_state:
                # Currently throttling - only stop if below low threshold
                if cpu < _THROTTLE_LOW_THRESHOLD:
                    _current_throttle_state = False
            else:
                # Not throttling - only start if above high threshold
                if cpu > _THROTTLE_HIGH_THRESHOLD:
                    _current_throttle_state = True
            return _current_throttle_state

    @staticmethod
    def get_optimal_worker_count(is_high_priority=False):
        """
        Returns the number of threads/processes to use.
        Args:
            is_high_priority: True if user explicitly requested the task (GUI open).
        """
        total_cores = os.cpu_count() or 4

        if is_high_priority:
            # Use all cores minus 1 (keep UI responsive)
            return max(1, total_cores - 1)

        if ResourceManager.should_throttle():
            return 1

        # Background mode: Use 25% of cores or 1
        return max(1, total_cores // 4)

    @staticmethod
    def is_gui_active():
        """
        Checks if the main application GUI is currently running.
        On Windows, looks for 'MacenaCS2Analyzer.exe' or 'python.exe' running 'main.py'.
        """
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                # 1. Check for frozen executable
                if proc.info["name"] == "MacenaCS2Analyzer.exe":
                    return True

                # 2. Check for python running main.py
                if "python" in proc.info["name"].lower():
                    cmd = proc.info["cmdline"]
                    if cmd and any("main.py" in arg for f, arg in enumerate(cmd)):
                        # Ensure it's NOT the current process (if service is py based)
                        if proc.pid != os.getpid():
                            return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    @staticmethod
    def set_low_priority():
        """Sets the current process to IDLE priority for background tasks."""
        if os.name == "nt":
            p = psutil.Process(os.getpid())
            p.nice(psutil.IDLE_PRIORITY_CLASS)
            logger.info("Process priority set to IDLE.")

    @staticmethod
    def set_high_priority():
        """Sets the current process to HIGH priority for maximum performance."""
        if os.name == "nt":
            try:
                p = psutil.Process(os.getpid())
                # Use psutil.HIGH_PRIORITY_CLASS instead of NORMAL
                # This ensures the process gets more CPU time from the Windows scheduler.
                p.nice(psutil.HIGH_PRIORITY_CLASS)
                logger.info("Process priority set to HIGH.")
            except Exception as e:
                logger.error("Failed to set HIGH priority: %s", e)
                # Fallback to Normal if High fails
                try:
                    p.nice(psutil.NORMAL_PRIORITY_CLASS)
                except Exception as e:  # noqa: BLE001
                    _ = e  # Intentionally suppressed

    @staticmethod
    def log_current_priority():
        """Logs the actual current process priority for verification."""
        if os.name == "nt":
            try:
                p = psutil.Process(os.getpid())
                p_class = p.nice()

                class_name = "UNKNOWN"
                if p_class == psutil.IDLE_PRIORITY_CLASS:
                    class_name = "IDLE"
                elif p_class == psutil.BELOW_NORMAL_PRIORITY_CLASS:
                    class_name = "BELOW_NORMAL"
                elif p_class == psutil.NORMAL_PRIORITY_CLASS:
                    class_name = "NORMAL"
                elif p_class == psutil.ABOVE_NORMAL_PRIORITY_CLASS:
                    class_name = "ABOVE_NORMAL"
                elif p_class == psutil.HIGH_PRIORITY_CLASS:
                    class_name = "HIGH"
                elif p_class == psutil.REALTIME_PRIORITY_CLASS:
                    class_name = "REALTIME"

                logger.info(
                    "[PRIORITY] Current Process Priority: %s_PRIORITY_CLASS (%s)",
                    class_name,
                    p_class,
                )
            except Exception as e:
                logger.error("Failed to check priority: %s", e)
