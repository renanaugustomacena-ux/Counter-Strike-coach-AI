# Control — Application Orchestration & Daemon Management

> **Authority:** Rule 2 (Backend Sovereignty), Rule 6 (Change Governance)
> **Skill:** `/state-audit`, `/resilience-check`

This module contains the central control plane for the Macena CS2 Analyzer. It manages the lifecycle of all background daemons, database health, ingestion queues, and ML training coordination.

## File Inventory

| File | Purpose | Key Classes |
|------|---------|-------------|
| `console.py` | Unified control console — singleton orchestrator | `Console`, `ServiceSupervisor`, `SystemState`, `ServiceStatus` |
| `db_governor.py` | Database tier health auditing + auto-recovery | `DatabaseGovernor` |
| `ingest_manager.py` | Ingestion queue controller (SINGLE/CONTINUOUS/TIMED) | `IngestionManager`, `IngestMode` |
| `ml_controller.py` | ML training lifecycle with cross-process safety locks | `MLControlContext`, `TrainingStopRequested` |

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

The `Console` singleton orchestrates startup:

```
1. DatabaseGovernor.audit_storage()
   ├── Check Tier 1/2 (monolith DB + WAL)
   ├── Check Tier 3 (per-match DBs)
   └── Auto-recover HLTV DB from .bak if missing
2. StateManager initialization
3. ServiceSupervisor start
   └── Start Hunter daemon (HLTV sync)
4. IngestionManager start
   └── Begin demo scanning
5. Ready for MLController (training on demand)
```

## Shutdown Sequence

```
1. Stop IngestionManager (drain queue)
2. Stop MLController (save checkpoint)
3. Stop ServiceSupervisor
   └── terminate() with 5s timeout → kill()
4. Save state
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
- Auto-restart: max 3 retries with exponential backoff
- Retry reset window: 3600s (resets counter if no crash in 1 hour)
- Monitor thread watches subprocess output with 3600s timeout
- Cancels pending restart timers on stop (prevents duplicate spawns)

### IngestionManager (Digester)

Three operational modes:
- **SINGLE**: Process one demo, then stop
- **CONTINUOUS**: Process all demos, then wait and re-scan
- **TIMED**: Re-scan every N minutes (default 30)

Thread-safe with `threading.Event` for graceful shutdown. Reports status: queued/processing/failed counts.

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
- Resource throttling is in `ingestion/resource_manager.py`, not here
