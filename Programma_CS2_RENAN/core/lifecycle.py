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
        # Pre-init so CORE-12 cleanup at launch_daemon() doesn't crash on the
        # first call (AttributeError: 'AppLifecycleManager' has no '_out_log').
        self._out_log = None
        self._err_log = None

    def ensure_single_instance(self):
        """
        Enforces the Single Instance Rule.
        Returns: True if this is the only instance, False otherwise.

        Windows: named kernel mutex. POSIX (F-0010): the in-house
        lock_files named lock — Linux IS the deploy target, and two
        instances mean concurrent SQLite writers, the exact hazard this
        guard exists to prevent ("fail closed to protect the DB").
        """
        if sys.platform != "win32":
            # F-0010: real enforcement via the TOCTOU-hardened named lock
            # (dead-PID reclaim included). Fail closed on conflict.
            try:
                from Programma_CS2_RENAN.core import lock_files

                lock_files.acquire("app_single_instance")
                self._instance_lock_name = "app_single_instance"
                return True
            except lock_files.LockConflict:
                logger.warning("Another instance of Macena CS2 Analyzer is already running.")
                return False
            except Exception:
                logger.exception("Single-instance lock could not be established — failing closed")
                return False

        try:
            kernel32 = ctypes.windll.kernel32
            self._instance_mutex = kernel32.CreateMutexW(None, True, self.mutex_name)
            last_error = kernel32.GetLastError()

            # R4 LOW: a NULL handle with any error other than 183 means the
            # mutex was NEVER created (e.g. access denied on the Global
            # namespace) — returning True would claim single-instance
            # protection that does not exist. Fail closed like the except.
            if not self._instance_mutex:
                logger.error(
                    "CreateMutexW returned NULL (GetLastError=%s) — "
                    "single-instance protection could not be established",
                    last_error,
                )
                return False

            # ERROR_ALREADY_EXISTS = 183
            if last_error == 183:
                logger.warning("Another instance of Macena CS2 Analyzer is already running.")
                return False

            return True
        except (OSError, AttributeError):
            # OSError covers ctypes.WinError (CreateMutexW failure, kernel32
            # access issues). AttributeError covers a hypothetical broken
            # windll.kernel32 lookup (already gated by sys.platform check).
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
            # F-0011: the daemon process writes its own rotating log file
            # (cs2_analyzer_daemon.log) instead of racing the app's file.
            env["CS2_LOG_ROLE"] = "daemon"

            # CORE-12: Close old handles before opening new ones on re-launch
            for handle in (self._out_log, self._err_log):
                if handle and not handle.closed:
                    handle.close()

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
            except (OSError, ValueError, subprocess.SubprocessError):
                # OSError: exec target missing / permission denied / fork failure.
                # ValueError: invalid Popen args (e.g. bad cwd type).
                # subprocess.SubprocessError: timing / IO setup failures.
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

        except (OSError, ValueError, subprocess.SubprocessError):
            # Same surface as inner Popen except above, plus open()-on-log-files
            # OSError (permissions / disk full / parent dir gone). All of these
            # leave the daemon unstarted; callers see None and surface a UI hint.
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
            except (OSError, ProcessLookupError, subprocess.SubprocessError):
                # OSError: signal delivery failed (target process gone / no perm).
                # ProcessLookupError: subclass of OSError; daemon already dead.
                # subprocess.SubprocessError: terminate/wait/kill internal failure.
                logger.exception("Error killing daemon")

        # Close daemon log handles to prevent resource leaks
        for handle in (getattr(self, "_out_log", None), getattr(self, "_err_log", None)):
            if handle:
                try:
                    handle.close()
                except OSError as e:
                    # Already closed / file gone — best-effort cleanup, debug only.
                    logger.debug("Failed to close daemon log handle: %s", e)

        # Mutex is released automatically by OS on process exit,
        # but explicit close is good hygiene.
        # F-0010: POSIX shutdown releases the named single-instance lock.
        if getattr(self, "_instance_lock_name", None) and sys.platform != "win32":
            try:
                from Programma_CS2_RENAN.core import lock_files

                lock_files.release(self._instance_lock_name)
            except Exception:
                logger.debug("single-instance lock release failed", exc_info=True)

        if self._instance_mutex and sys.platform == "win32":
            try:
                ctypes.windll.kernel32.CloseHandle(self._instance_mutex)
            except OSError as e:
                # Win32 CloseHandle raises OSError on bad handle; non-fatal at exit.
                logger.debug("Mutex cleanup: %s", e)


# Global Singleton
lifecycle = AppLifecycleManager()
