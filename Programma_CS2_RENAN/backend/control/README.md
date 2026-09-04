# Control — Application Orchestration & Daemon Management

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 2 (Backend Sovereignty), Rule 6 (Change Governance)
> **Skill:** `/state-audit`, `/resilience-check`

This module contains the central control plane for the Macena CS2 Analyzer. It manages the lifecycle of all background daemons, database health, ingestion queues, and ML training coordination.

## File Inventory

| File | Purpose | Key Classes |
|------|---------|-------------|
| `console.py` | Unified control console — singleton orchestrator | `Console`, `ServiceSupervisor`, `SystemState`, `ServiceStatus` |
| `db_governor.py` | Database tier health auditing + auto-recovery | `DatabaseGovernor` |
| `ingest_manager.py` | Ingestion queue controller (SINGLE/CONTINUOUS/TIMED) | `IngestionManager`, `IngestMode` |
| `ml_controller.py` | ML training lifecycle with cross-process safety locks | `MLController`, `MLControlContext`, `TrainingStopRequested` |

## System States

```
IDLE ──> BOOTING ──> BUSY ──> IDLE
                       │
                       ├──> MAINTENANCE
                       └──> ERROR
                             │
                             └──> SHUTTING_DOWN
```

## Boot Sequence

The `Console` singleton orchestrates startup (`boot()`):

```
1. Hunter daemon start (only if ENABLE_HLTV_SYNC=true)
   ├── docker_manager.ensure_flaresolverr()
   └── ServiceSupervisor.start_service("hunter")
       (skipped with a user notification if Docker is unavailable)
2. init_database() — create missing tables/columns
3. DatabaseGovernor audit
   ├── audit_storage(): Tier 1/2 (monolith DB + WAL), Tier 3 (per-match DBs)
   ├── Auto-restore hltv_metadata.db from .bak if missing
   └── verify_integrity() — flags ERROR state on monolith failure
4. Log retention enforcement (OBS-06)
5. Belief confidence computed from PlayerMatchStats count
   (IngestionManager and MLController start on demand, not at boot)
```

## Shutdown Sequence

```
1. Stop MLController (request training stop)
2. Stop IngestionManager (signal stop event)
3. Stop Hunter via ServiceSupervisor
   └── terminate() with 5s timeout → kill()
4. Stop FlareSolverr container (docker stop)
5. Drain wait: up to 5s for ML/ingestion to report stopped
6. State set to Offline (idempotent — safe to call twice)
```

## Tri-Daemon Architecture

The `Console` manages three daemon types:

| Daemon | Controller | Purpose |
|--------|-----------|---------|
| **Hunter** | `ServiceSupervisor` | HLTV pro stats scraping (subprocess) |
| **Digester** | `IngestionManager` | Demo parsing + feature extraction (thread) |
| **Teacher** | `MLController` | Neural network training (thread with file lock) |

### ServiceSupervisor (Hunter)

- Spawns Hunter as a subprocess with `PYTHONPATH` setup
- Auto-restart: max 3 retries with a fixed 5s restart delay
- Retry reset window: 3600s (resets counter if no crash in 1 hour)
- Monitor thread watches subprocess output with 3600s timeout
- Cancels pending restart timers on stop (prevents duplicate spawns)

### IngestionManager (Digester)

Three operational modes:
- **SINGLE**: Process one demo, then stop
- **CONTINUOUS**: Process all demos, then wait and re-scan
- **TIMED**: Re-scan every N minutes (default 30)

Thread-safe with `threading.Event` for graceful shutdown. Processes at most 10 demos per cycle (WR-07, `_MAX_BATCH_SIZE`) to prevent CPU hogging. Reports status: queued/processing/failed counts.

### MLController (Teacher)

- `MLControlContext`: Control token passed to training loops
  - `check_state()`: Called per batch — raises `TrainingStopRequested` on stop
  - Pause support with `Event.wait()` (no busy-waiting)
  - Throttle factor: 0.0 (full speed) to 1.0 (max delay)
- **Cross-process file lock** (`training.lock`): Prevents concurrent training
  - Uses `fcntl` (Unix) / `msvcrt` (Windows)
  - Non-blocking: raises `RuntimeError` if lock held
  - PID-based tracking for debugging

## Lock Ordering (Critical)

```
Console._lock  >  ServiceSupervisor._lock
```

Console never acquires ServiceSupervisor's lock while holding its own, and vice versa. Violating this ordering risks deadlock.

## Development Notes

- `Console` is a singleton — safe to call from any thread
- All public methods in `Console` are thread-safe
- `DatabaseGovernor.audit_storage()` returns anomaly list for logging
- `IngestMode` enum prevents invalid mode strings
- `TrainingStopRequested` exception provides clean abort mechanism for long training runs
- Resource throttling is in `backend/ingestion/resource_manager.py`, not here
