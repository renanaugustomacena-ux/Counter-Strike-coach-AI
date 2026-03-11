import atexit
import ctypes
import os
import subprocess
import sys
from pathlib import Path

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.lifecycle")


class AppLifecycleManager:
    """
    Centralized controller for Application Startup, Single-Instance Locking,
    and Daemon Process Management.
    """

    _instance_mutex = None
    _daemon_process = None

    def __init__(self):
        self.mutex_name = "Global\\MacenaCS2Analyzer_Unique_Lock_v1"
        # lifecycle.py is at Programma_CS2_RENAN/core/lifecycle.py
        # We need the parent of Programma_CS2_RENAN (Macena_cs2_analyzer)
        self.project_root = Path(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )

    def ensure_single_instance(self):
        """
        Enforces Single Instance Rule using Windows Named Mutex.
        Returns: True if this is the only instance, False otherwise.

        Note: On non-Windows platforms this is a no-op (always returns True)
        because the project currently targets Windows-only deployments.
        """
        if sys.platform != "win32":
            # Non-Windows: no single-instance enforcement (Windows-centric project)
            return True

        try:
            kernel32 = ctypes.windll.kernel32
            self._instance_mutex = kernel32.CreateMutexW(None, True, self.mutex_name)
            last_error = kernel32.GetLastError()

            # ERROR_ALREADY_EXISTS = 183
            if last_error == 183:
                logger.warning("Another instance of Macena CS2 Analyzer is already running.")
                return False

            return True
        except Exception as e:
            logger.exception("Failed to acquire single instance lock")
            # Fail closed to protect DB
            return False

    def launch_daemon(self):
        """
        Launches the Session Engine daemon (Scanner/Digester/Teacher).
        Returns the Popen object.
        """
        if self._daemon_process and self._daemon_process.poll() is None:
            return self._daemon_process

        script_path = self.project_root / "Programma_CS2_RENAN" / "core" / "session_engine.py"
        if not script_path.exists():
            logger.critical("Session Engine not found at %s", script_path)
            return None

        try:
            cmd = [sys.executable, str(script_path)]

            # Prepare Environment
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.project_root) + os.pathsep + env.get("PYTHONPATH", "")

            # Redirect Output — keep handles for cleanup
            self._out_log = open(self.project_root / "daemon_out.log", "w")
            self._err_log = open(self.project_root / "daemon_err.log", "w")

            try:
                self._daemon_process = subprocess.Popen(
                    cmd,
                    cwd=str(self.project_root),
                    stdin=subprocess.PIPE,  # For IPC signaling capability
                    stdout=self._out_log,
                    stderr=self._err_log,
                    env=env,
                )
            except Exception:
                # Close file handles immediately if Popen fails to prevent leaks
                self._out_log.close()
                self._err_log.close()
                self._out_log = None
                self._err_log = None
                raise

            logger.info("Session Daemon launched (PID: %s)", self._daemon_process.pid)

            # Register generic cleanup
            atexit.register(self.shutdown)
            return self._daemon_process

        except Exception as e:
            logger.exception("Failed to launch daemon")
            return None

    def shutdown(self):
        """
        Gracefully terminates the daemon and releases resources.
        """
        if self._daemon_process and self._daemon_process.poll() is None:
            logger.info("Terminating Session Daemon...")
            try:
                # 1. Try gentle termination
                self._daemon_process.terminate()
                try:
                    self._daemon_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # 2. Force kill if resistant
                    logger.warning("Daemon hung, forcing kill.")
                    self._daemon_process.kill()
            except Exception as e:
                logger.exception("Error killing daemon")

        # Close daemon log handles to prevent resource leaks
        for handle in (getattr(self, "_out_log", None), getattr(self, "_err_log", None)):
            if handle:
                try:
                    handle.close()
                except Exception as e:
                    logger.debug("Failed to close daemon log handle: %s", e)

        # Mutex is released automatically by OS on process exit,
        # but explicit close is good hygiene.
        if self._instance_mutex and sys.platform == "win32":
            try:
                ctypes.windll.kernel32.CloseHandle(self._instance_mutex)
            except Exception as e:
                logger.debug("Mutex cleanup: %s", e)


# Global Singleton
lifecycle = AppLifecycleManager()
