"""
Unified Control Console — singleton orchestrator for all backend subsystems.

Manages: ServiceSupervisor (Hunter subprocess), IngestionManager, MLController,
DatabaseGovernor.  Provides boot/shutdown lifecycle, aggregate health status,
and ML training wrappers.

Lock ordering (must never be violated):
    Console._lock  >  ServiceSupervisor._lock
    (Console never acquires ServiceSupervisor._lock while holding Console._lock;
     ServiceSupervisor never acquires Console._lock.)

Thread safety: Console is a singleton created under _lock.  All public methods
are safe to call from any thread.
"""

import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict

from Programma_CS2_RENAN.backend.storage.state_manager import DaemonName, get_state_manager
from Programma_CS2_RENAN.observability.error_codes import ErrorCode, log_with_code
from Programma_CS2_RENAN.observability.logger_setup import get_logger, set_correlation_id

logger = get_logger("cs2analyzer.console")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SystemState(Enum):
    IDLE = "idle"
    BOOTING = "booting"
    BUSY = "busy"
    SHUTTING_DOWN = "shutting_down"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class ServiceStatus(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    CRASHED = "crashed"
    STARTING = "starting"


# ---------------------------------------------------------------------------
# ServiceSupervisor — manages background subprocess daemons
# ---------------------------------------------------------------------------


class ServiceSupervisor:
    """
    Authoritative supervisor for background daemons.
    Manages PIDs, liveness, auto-restart with backoff.
    """

    _MAX_RETRIES: int = 3
    _RETRY_RESET_WINDOW_S: float = 3600.0
    _RESTART_DELAY_S: float = 5.0
    _MONITOR_TIMEOUT_S: float = 3600.0  # D4: kill subprocess after 1h unresponsive

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.services: Dict[str, Dict] = {
            "hunter": {
                "script": "Programma_CS2_RENAN/hltv_sync_service.py",
                "process": None,
                "status": ServiceStatus.STOPPED,
                "last_start": None,
                "retries": 0,
                "restart_pending": False,
                "restart_timer": None,  # D5: stored for cancellation
            }
        }
        self._lock = threading.Lock()

    def start_service(self, name: str):
        with self._lock:
            if name not in self.services:
                raise ValueError(f"Unknown service: {name}")

            svc = self.services[name]
            if svc["status"] == ServiceStatus.RUNNING:
                return

            # NN-85: Reset retry counter on manual start
            svc["retries"] = 0
            # R3-H06: Clear pending restart state
            svc["restart_pending"] = False
            svc["restart_timer"] = None

            logger.info("Supervisor: Starting service '%s'...", name)
            svc["status"] = ServiceStatus.STARTING

            try:
                script_path = self.project_root / svc["script"]

                env = os.environ.copy()
                env["PYTHONPATH"] = str(self.project_root) + (
                    os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else ""
                )

                process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    cwd=str(self.project_root),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )

                svc["process"] = process
                svc["status"] = ServiceStatus.RUNNING
                svc["last_start"] = datetime.now(timezone.utc)
                logger.info("Supervisor: Service '%s' started with PID %s", name, process.pid)

                threading.Thread(
                    target=self._monitor_process, args=(name, process), daemon=True
                ).start()

            except Exception as e:
                svc["status"] = ServiceStatus.CRASHED
                logger.error("Supervisor: Failed to start service '%s': %s", name, e, exc_info=True)

    def stop_service(self, name: str):
        with self._lock:
            svc = self.services.get(name)
            if not svc:
                return

            # D5: Cancel any pending restart timer before stopping
            timer = svc.get("restart_timer")
            if timer:
                timer.cancel()
                svc["restart_timer"] = None
            svc["restart_pending"] = False

            if not svc["process"]:
                return

            logger.info("Supervisor: Stopping service '%s'...", name)
            process = svc["process"]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

            svc["status"] = ServiceStatus.STOPPED
            svc["process"] = None
            logger.info("Supervisor: Service '%s' stopped.", name)

    def _monitor_process(self, name: str, process: subprocess.Popen):
        """Threaded monitor for a service process."""
        # D4: Timeout prevents infinite block on unbounded subprocess output
        try:
            stdout, stderr = process.communicate(timeout=self._MONITOR_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            logger.error(
                log_with_code(
                    ErrorCode.CO_03,
                    "Supervisor: Service '%s' killed after %ss monitor timeout",
                ),
                name,
                self._MONITOR_TIMEOUT_S,
            )

        exit_code = process.returncode

        with self._lock:
            svc = self.services[name]
            if svc["status"] == ServiceStatus.STOPPED:
                return  # Manual stop — don't restart

            svc["status"] = ServiceStatus.CRASHED
            svc["process"] = None
            logger.error("Supervisor: Service '%s' exited with code %s", name, exit_code)
            if stderr:
                logger.error("Supervisor: Service '%s' stderr: %s", name, stderr[:2000])

            # Auto-restart: max _MAX_RETRIES in _RETRY_RESET_WINDOW_S, then give up.
            last_start = svc.get("last_start")
            if (
                last_start
                and (datetime.now(timezone.utc) - last_start).total_seconds()
                > self._RETRY_RESET_WINDOW_S
            ):
                svc["retries"] = 0

            # R3-H06: Guard against duplicate restart timers
            if svc.get("restart_pending"):
                logger.debug("Supervisor: Restart already pending for '%s', skipping.", name)
            elif svc["retries"] < self._MAX_RETRIES:
                svc["retries"] += 1
                svc["restart_pending"] = True
                logger.warning(
                    "Supervisor: Auto-restarting '%s' (attempt %s/%s)...",
                    name,
                    svc["retries"],
                    self._MAX_RETRIES,
                )
                # D5: Store timer reference so stop_service() can cancel it
                timer = threading.Timer(self._RESTART_DELAY_S, self.start_service, args=(name,))
                svc["restart_timer"] = timer
                timer.start()
            else:
                logger.error(
                    log_with_code(
                        ErrorCode.CO_04,
                        "Supervisor: Service '%s' exceeded max retries (%s). "
                        "Manual restart required.",
                    ),
                    name,
                    self._MAX_RETRIES,
                )

    def get_status(self) -> Dict:
        with self._lock:
            return {
                name: {
                    "status": svc["status"].value,
                    "last_start": svc["last_start"].isoformat() if svc["last_start"] else None,
                    "pid": svc["process"].pid if svc["process"] else None,
                }
                for name, svc in self.services.items()
            }


# ---------------------------------------------------------------------------
# Console — singleton orchestrator
# ---------------------------------------------------------------------------


class Console:
    """
    The Unified Control Console (Singleton).
    Authority for ML, Ingestion, and System State.

    D1 fix: Initialization happens inside __new__ under _lock.  The __init__
    method is intentionally empty.  This eliminates the race where two threads
    could both enter __init__ with _initialized == False.
    """

    _BASELINE_CACHE_TTL_S: float = 60.0
    _TRAINING_DATA_CACHE_TTL_S: float = 120.0

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        # D1: All initialization under lock — no race possible
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._do_init()
                # Only assign after _do_init succeeds — if it throws,
                # _instance stays None and next call retries cleanly
                cls._instance = inst
            return cls._instance

    def __init__(self):
        pass  # D1: All work done in _do_init() under lock

    def _do_init(self):
        """Called exactly once, under Console._lock. No race possible."""
        current_file = Path(__file__).resolve()
        self.project_root = current_file.parent.parent.parent.parent

        # D7: Lifecycle flags
        self._shutdown_done = False
        self._booting = False
        self._shutting_down = False

        # D3: No more self.state — state is always computed live.
        # Only this flag persists to signal DB corruption.
        self._db_integrity_failed = False

        self.supervisor = ServiceSupervisor(self.project_root)

        from Programma_CS2_RENAN.backend.control.db_governor import DatabaseGovernor
        from Programma_CS2_RENAN.backend.control.ingest_manager import IngestionManager
        from Programma_CS2_RENAN.backend.control.ml_controller import MLController

        self.ingest_manager = IngestionManager()
        self.db_governor = DatabaseGovernor()
        self.ml_controller = MLController()

        # Caches for expensive status queries
        self._baseline_cache = None
        self._baseline_cache_ts = 0.0

        self._training_data_cache = None
        self._training_data_cache_ts = 0.0

        logger.info("Unified Control Console Initialized.")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def boot(self):
        """System-wide startup sequence."""
        # D10: Correlation ID for tracing the entire boot sequence
        set_correlation_id()
        self._booting = True

        # D9: Make boot visible to all processes via CoachState
        sm = get_state_manager()
        sm.update_status(DaemonName.GLOBAL, "Booting", "System boot sequence started")

        logger.info("Console: Booting system subsystems...")

        try:
            # 1. Start Hunter service (if HLTV sync is enabled)
            from Programma_CS2_RENAN.core.config import get_setting

            if get_setting("ENABLE_HLTV_SYNC", False):
                from Programma_CS2_RENAN.backend.data_sources.hltv.docker_manager import (
                    ensure_flaresolverr,
                )

                docker_ok = ensure_flaresolverr(str(self.project_root))
                if docker_ok:
                    self.supervisor.start_service("hunter")
                    time.sleep(1)
                    svcs = self.supervisor.get_status()
                    hunter_status = svcs.get("hunter", {}).get("status", "unknown")
                    if hunter_status != "running":
                        logger.warning("Console: Hunter status after boot: %s", hunter_status)
                else:
                    logger.warning(
                        "Console: FlareSolverr unavailable. Hunter not started. "
                        "Start Docker Desktop and retry."
                    )
            else:
                logger.info("Console: HLTV sync disabled (ENABLE_HLTV_SYNC=False). Hunter skipped.")

            # 2. Initialize database schema (creates missing tables + adds missing columns)
            from Programma_CS2_RENAN.backend.storage.database import init_database

            init_database()
            logger.info("Console: Database schema initialized.")

            # 3. Check DB Integrity
            self._audit_databases()

            # 4. OBS-06: Enforce log retention policy (purge old log files)
            from Programma_CS2_RENAN.observability.logger_setup import configure_retention

            configure_retention()

            # 5. Compute and persist belief confidence from current match count
            try:
                from sqlmodel import func, select

                from Programma_CS2_RENAN.backend.storage.database import get_db_manager as _get_db
                from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

                with _get_db().get_session() as s:
                    match_count = s.exec(
                        select(func.count(PlayerMatchStats.id))
                    ).one() or 0

                if match_count >= 200:
                    confidence = 100.0
                elif match_count >= 50:
                    confidence = 80.0
                elif match_count > 0:
                    confidence = 50.0
                else:
                    confidence = 0.0

                sm.update_belief_confidence(confidence)
                logger.info("Console: Belief confidence set to %.0f%% (%d matches)", confidence, match_count)
            except Exception as e:
                logger.warning("Console: Could not compute belief confidence: %s", e)

            logger.info("Console: System boot complete.")
            sm.update_status(DaemonName.GLOBAL, "Running", "System boot complete")
        except Exception:
            logger.error(log_with_code(ErrorCode.CO_01, "Boot sequence failed"))
            sm.update_status(DaemonName.GLOBAL, "Error", "Boot sequence failed")
            raise
        finally:
            self._booting = False

    def shutdown(self):
        """Graceful shutdown of all subsystems."""
        # D7: Idempotency guard — safe to call multiple times
        if self._shutdown_done:
            return
        self._shutdown_done = True
        self._shutting_down = True

        # D10: Correlation ID for tracing the shutdown sequence
        set_correlation_id()

        # D9: Make shutdown visible via CoachState
        sm = get_state_manager()
        sm.update_status(DaemonName.GLOBAL, "ShuttingDown", "Graceful shutdown initiated")

        logger.info("Console: Initiating graceful shutdown...")

        # Ordered shutdown: training → ingestion → Hunter → FlareSolverr
        # Each call is isolated so one failure doesn't prevent the rest from stopping.
        for label, fn in [
            ("ML training", self.ml_controller.stop_training),
            ("Ingestion", self.ingest_manager.stop),
            ("Hunter service", lambda: self.supervisor.stop_service("hunter")),
        ]:
            try:
                fn()
            except Exception as e:
                logger.error("Console: Failed to stop %s during shutdown: %s", label, e)

        try:
            from Programma_CS2_RENAN.backend.data_sources.hltv.docker_manager import (
                stop_flaresolverr,
            )

            stop_flaresolverr()
        except Exception as e:
            logger.error("Console: Failed to stop FlareSolverr during shutdown: %s", e)

        # Wait for async subsystems to drain
        _shutdown_clean = False
        for _ in range(10):
            ml_status = self.ml_controller.get_status()
            ingest_status = self.ingest_manager.get_status()
            if not ml_status.get("is_running") and not ingest_status.get("is_running"):
                _shutdown_clean = True
                break
            time.sleep(0.5)

        if not _shutdown_clean:
            logger.warning(
                log_with_code(
                    ErrorCode.CO_02,
                    "Shutdown timeout — subsystems may still be running "
                    "(ML=%s, Ingest=%s). Process exit will force termination.",
                ),
                self.ml_controller.get_status().get("is_running"),
                self.ingest_manager.get_status().get("is_running"),
            )

        sm.update_status(DaemonName.GLOBAL, "Offline", "Shutdown complete")
        logger.info("Console: Shutdown complete.")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _audit_databases(self):
        """Verifies presence and integrity of Tier 1 & 2 databases."""
        try:
            audit = self.db_governor.audit_storage()
            logger.info(
                "Console: Storage Audit - T1/2: %.2fMB, T3: %s matches",
                audit["tier1_2_size"] / (1024 * 1024),
                audit["tier3_count"],
            )

            integrity = self.db_governor.verify_integrity()
            if not integrity.get("monolith"):
                logger.error("Console: MONOLITH INTEGRITY FAILURE!")
                self._db_integrity_failed = True
            else:
                # D3: Clear previous failure if integrity is now OK
                self._db_integrity_failed = False
                logger.info("Console: Database Tier 1/2 connection verified.")
        except Exception as e:
            logger.error("Console: Database audit failed: %s", e)
            self._db_integrity_failed = True

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_system_status(self) -> Dict:
        """Aggregate health report with per-subsystem error isolation."""

        def _safe_call(label, fn):
            try:
                return fn()
            except Exception as e:
                logger.warning("Console: Status fetch failed for '%s': %s", label, e)
                return {"error": str(e)}

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": self._compute_state(),
            "services": _safe_call("services", self.supervisor.get_status),
            "teacher": _safe_call("teacher", lambda: get_state_manager().get_status("teacher")),
            "ml_controller": _safe_call("ml_controller", self.ml_controller.get_status),
            "ingestion": _safe_call("ingestion", self.ingest_manager.get_status),
            "storage": _safe_call("storage", self.db_governor.audit_storage),
            "baseline": self._get_baseline_status(),
            "training_data": _safe_call("training_data", self._get_training_data_progress),
        }

    def _compute_state(self) -> str:
        """
        D2+D3: Compute live system state from ALL subsystem health.
        Never caches — always reflects current reality.

        Priority order:
        1. Shutting down / booting (explicit lifecycle)
        2. DB integrity failure
        3. Any supervised service crashed
        4. CoachState daemon statuses contain "Error"
        5. ML or ingestion actively running → BUSY
        6. Otherwise → IDLE

        Note: Session engine heartbeat staleness is NOT treated as ERROR.
        A stale heartbeat simply means the session engine isn't running
        (e.g., console-only mode, before first demo ingest), which is normal.
        """
        # Lifecycle overrides
        if self._shutting_down:
            return SystemState.SHUTTING_DOWN.value
        if self._booting:
            return SystemState.BOOTING.value

        # DB corruption
        if self._db_integrity_failed:
            return SystemState.ERROR.value

        # Supervised services
        try:
            svcs = self.supervisor.get_status()
            if any(s.get("status") == "crashed" for s in svcs.values()):
                return SystemState.ERROR.value
        except Exception:
            pass  # Non-fatal — supervisor may not be initialized yet

        # CoachState daemon statuses (Hunter, Digester, Teacher)
        try:
            state = get_state_manager().get_state()
            daemon_statuses = [state.hltv_status, state.ingest_status, state.ml_status]
            if any(s == "Error" for s in daemon_statuses):
                return SystemState.ERROR.value
        except Exception:
            pass  # CoachState may not exist yet (first boot)

        # Active work
        try:
            ml_running = self.ml_controller.get_status().get("is_running", False)
            ingest_running = self.ingest_manager.get_status().get("is_running", False)
            if ml_running or ingest_running:
                return SystemState.BUSY.value
        except Exception:
            pass

        return SystemState.IDLE.value

    def _get_baseline_status(self) -> Dict:
        """Get temporal baseline health status. Cached for 60s on success."""
        now = time.monotonic()
        if (
            self._baseline_cache is not None
            and (now - self._baseline_cache_ts) < self._BASELINE_CACHE_TTL_S
        ):
            return self._baseline_cache

        try:
            from sqlmodel import func, select

            from Programma_CS2_RENAN.backend.processing.baselines.pro_baseline import (
                TemporalBaselineDecay,
            )
            from Programma_CS2_RENAN.backend.storage.database import get_hltv_db_manager
            from Programma_CS2_RENAN.backend.storage.db_models import ProPlayerStatCard

            db = get_hltv_db_manager()
            with db.get_session() as session:
                card_count = session.exec(select(func.count(ProPlayerStatCard.id))).one()

            decay = TemporalBaselineDecay()
            temporal = decay.get_temporal_baseline()

            result = {
                "stat_cards": card_count,
                "temporal_metrics": len(temporal),
                "mode": "temporal" if card_count >= 10 else "legacy",
            }
            # D8: Only cache successful results
            self._baseline_cache = result
            self._baseline_cache_ts = now
            return result
        except Exception as e:
            logger.warning("Console: Baseline status fetch failed: %s", e)
            # D8: Don't cache errors — next call will retry immediately
            self._baseline_cache = None
            return {"stat_cards": 0, "temporal_metrics": 0, "mode": "unavailable"}

    def _get_training_data_progress(self) -> Dict:
        """Report .dem files processed vs available. Cached for 120s on success."""
        now = time.monotonic()
        if (
            self._training_data_cache is not None
            and (now - self._training_data_cache_ts) < self._TRAINING_DATA_CACHE_TTL_S
        ):
            return self._training_data_cache

        from sqlmodel import func, select

        from Programma_CS2_RENAN.backend.storage.database import get_db_manager
        from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
        from Programma_CS2_RENAN.core.config import get_setting

        db = get_db_manager()

        with db.get_session() as session:
            pro_processed = session.exec(
                select(func.count(PlayerMatchStats.id)).where(
                    PlayerMatchStats.is_pro == True
                )  # noqa: E712
            ).one()
            user_processed = session.exec(
                select(func.count(PlayerMatchStats.id)).where(
                    PlayerMatchStats.is_pro == False
                )  # noqa: E712
            ).one()
            trained_on = session.exec(
                select(func.count(PlayerMatchStats.id)).where(
                    PlayerMatchStats.dataset_split == "train"
                )
            ).one()

        # Count .dem files on disk
        _DEMO_COUNT_CAP = 10_000

        def _count_demos(directory: Path) -> int:
            try:
                count = 0
                for _ in directory.rglob("*.dem"):
                    count += 1
                    if count >= _DEMO_COUNT_CAP:
                        logger.warning("Demo count capped at %s in %s", _DEMO_COUNT_CAP, directory)
                        return count
                return count
            except Exception as exc:
                logger.warning("Failed to count demos in %s: %s", directory, exc)
                return 0

        pro_dem_available = 0
        user_dem_available = 0

        pro_path = get_setting("PRO_DEMO_PATH", "")
        if pro_path:
            pro_dir = Path(pro_path)
            if pro_dir.exists():
                pro_dem_available = _count_demos(pro_dir)

        user_path = get_setting("USER_DEMO_PATH", "")
        if user_path:
            user_dir = Path(user_path)
            if user_dir.exists():
                user_dem_available = _count_demos(user_dir)

        total_processed = pro_processed + user_processed
        total_available = pro_dem_available + user_dem_available

        result = {
            "pro_demos_processed": pro_processed,
            "user_demos_processed": user_processed,
            "total_processed": total_processed,
            "pro_dem_on_disk": pro_dem_available,
            "user_dem_on_disk": user_dem_available,
            "total_on_disk": total_available,
            "trained_on": trained_on,
            "ready_for_training": total_processed >= 10,
        }

        self._training_data_cache = result
        self._training_data_cache_ts = now
        return result

    # ------------------------------------------------------------------
    # ML Control Wrappers
    # ------------------------------------------------------------------

    def start_training(self):
        self.ml_controller.start_training()
        return self.ml_controller.get_status()

    def stop_training(self):
        self.ml_controller.stop_training()
        return self.ml_controller.get_status()

    def pause_training(self):
        self.ml_controller.pause_training()
        return self.ml_controller.get_status()

    def resume_training(self):
        self.ml_controller.resume_training()
        return self.ml_controller.get_status()


# ---------------------------------------------------------------------------
# Global entry point
# ---------------------------------------------------------------------------


def get_console() -> Console:
    return Console()
