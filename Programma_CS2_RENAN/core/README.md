# Core Systems

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Authority:** `Programma_CS2_RENAN/core/`
Runtime foundation providing daemon orchestration, configuration management,
spatial intelligence, and application lifecycle control.

## Introduction

The `core/` package is the heartbeat of Macena CS2 Analyzer. It hosts the
Quad-Daemon session engine that keeps the analysis pipeline running, the
three-level configuration system that resolves user settings at runtime, the
spatial data layer that maps all nine competitive CS2 maps into coordinate
space, and the lifecycle manager that enforces single-instance execution.
Every other package in the project depends on at least one module from `core/`.

## File Inventory

| File | Purpose |
|------|---------|
| `session_engine.py` | Quad-Daemon Engine: Hunter, Digester, Teacher, Pulse |
| `config.py` | Three-level config resolution (defaults, JSON, keyring) |
| `spatial_data.py` | `MapMetadata` for 9 maps, Z-level support, coordinate transforms |
| `spatial_engine.py` | `SpatialEngine`: world-to-pixel and pixel-to-world conversions |
| `map_manager.py` | `MapManager`: UI-facing asset loading with async Kivy support |
| `lifecycle.py` | `AppLifecycleManager`: single-instance mutex, daemon launch/shutdown |
| `constants.py` | Project-wide constants: tick rate, FOV, utility durations, trade window |
| `demo_frame.py` | Core data types: `PlayerState`, `GhostState`, `NadeState`, `DemoFrame` |
| `asset_manager.py` | `SmartAsset` (lazy loading), `AssetAuthority` (centralized registry) |
| `playback_engine.py` | `PlaybackEngine`: interpolated demo replay with frame blending |
| `localization.py` | `LocalizationManager`: English, Italian, Portuguese string tables |
| `platform_utils.py` | Cross-platform drive detection (Windows, Linux, macOS) |
| `registry.py` | `ScreenRegistry` for Kivy screen lifecycle management |
| `logger.py` | Structured logging setup with module-level loggers |
| `app_types.py` | Shared type aliases and enums used across the application |
| `frozen_hook.py` | PyInstaller runtime hook for frozen-build path correction |
| `integrity_manifest.json` | File hash manifest for RASP runtime integrity verification |

## Quad-Daemon Engine (`session_engine.py`)

The session engine launches four daemon threads plus an `IngestionWatcher`,
coordinated through `threading.Event` signals and a central `CoachState` row
in the monolith database.

```
+----------------------------------------------------+
|              run_session_loop()                     |
|                                                    |
|  1. init_database()                                |
|  2. BackupManager.create_checkpoint("startup")     |
|  3. Knowledge base init (if empty)                 |
|  4. _monitor_stdin (parent-death detection)        |
|  5. Launch daemons:                                |
|                                                    |
|     +----------+  +-----------+  +---------+       |
|     |  Hunter  |  | Digester  |  | Teacher |       |
|     | (Scanner)|  | (Worker)  |  | (ML)    |       |
|     +----------+  +-----------+  +---------+       |
|          |              |              |            |
|     File scan      Queue consume  Retrain check    |
|     10s cycle      Event-driven   5min cycle       |
|                                                    |
|     +----------+                                   |
|     |  Pulse   |  Heartbeat every 5 seconds        |
|     +----------+                                   |
+----------------------------------------------------+
```

### Daemon Responsibilities

- **Hunter (_scanner_daemon_loop):** Scans user and pro demo directories every
  10 seconds when active. Calls `process_new_demos()` to queue new files.
  Runs periodic disk-space checks every 5 minutes.

- **Digester (_digester_daemon_loop):** Consumes the ingestion queue one task at
  a time. Uses `_work_available_event` for efficient wake-up (avoids polling).
  Processes pro demos with higher priority.

- **Teacher (_teacher_daemon_loop):** Checks if new pro samples exceed a 10%
  growth threshold, then triggers `CoachTrainingManager.run_full_cycle()`.
  Also runs belief calibration and meta-shift detection after each retraining.
  Respects the module-level `_TRAINING_LOCK` to prevent concurrent training.

- **Pulse (_pulse_daemon_loop):** Updates the `last_heartbeat` timestamp on
  `CoachState` every 5 seconds to prove daemon liveness to the UI.

### Shutdown Protocol

Parent death is detected via stdin pipe closure (`_monitor_stdin`). The
`_shutdown_event` is set, all daemons exit their loops, and threads are joined
with a 5-second timeout each.

## Configuration System (`config.py`)

Three-level resolution: hardcoded defaults, `user_settings.json` on disk, and
OS keyring for secrets (Steam API key, Faceit API key).

```
  Hardcoded defaults (load_user_settings)
            |
            v
  user_settings.json  (SETTINGS_PATH)
            |
            v
  OS keyring (keyring.get_password)
            |
            v
  Module-level globals (CS2_PLAYER_NAME, STEAM_API_KEY, ...)
```

### Thread Safety

- `get_setting(key)` / `get_credential(key)` -- acquire `_settings_lock`, always current
- Module-level globals (`CS2_PLAYER_NAME`, etc.) -- snapshot at import, **stale in daemon
  threads**; use `get_setting()` instead
- `save_user_setting(key, value)` -- atomic write via tmp file + `os.replace()`
- `refresh_settings()` -- reloads from disk under lock, updates globals

### Path Architecture

```
CORE_DB_DIR    = BASE_DIR/backend/storage/     (database.db ALWAYS here)
USER_DATA_ROOT = BRAIN_DATA_ROOT or BASE_DIR   (models, logs, cache)
MATCH_DATA_PATH = PRO_DEMO_PATH/match_data/    (or fallback in-project)
```

The core database stays in the project folder for portability. `BRAIN_DATA_ROOT`
affects only regeneratable artifacts (models, logs, cache).

## Spatial Intelligence

### spatial_data.py

Defines `MapMetadata` (frozen dataclass) for all nine competitive CS2 maps with
support for multi-level maps (Nuke, Vertigo) via Z-axis cutoff thresholds.

Key functions:
- `get_map_metadata(map_name)` -- fuzzy lookup with partial matching and ambiguity warnings
- `get_map_metadata_for_z(map_name, z)` -- automatic level selection based on Z coordinate
- `compute_z_penalty(z_position, map_name)` -- normalized [0, 1] penalty for the 25-dim vector
- `classify_vertical_level(z, map_name)` -- returns "upper", "lower", "transition", or "default"

Configuration is loaded from `data/map_config.json` with hardcoded fallbacks in
`_FALLBACK_REGISTRY` (sourced from Valve radar overview files).

### spatial_engine.py

`SpatialEngine` provides coordinate transformation between Source 2 world
coordinates and UI pixel space:

- `world_to_normalized()` -- world coords to [0, 1] radar space
- `normalized_to_pixel()` / `pixel_to_normalized()` -- viewport scaling
- `world_to_pixel()` / `pixel_to_world()` -- direct conversion shortcuts

### constants.py

Project-wide temporal constants derived from `TICK_RATE = 64`:

| Constant | Seconds | Ticks |
|----------|---------|-------|
| `SMOKE_DURATION` | 18.0 | 1152 |
| `MOLOTOV_DURATION` | 7.0 | 448 |
| `FLASH_DURATION` | 2.0 | 128 |
| `MEMORY_DECAY_TAU` | 2.5 | 160 |
| `MEMORY_CUTOFF` | 7.5 | 480 |
| `TRADE_WINDOW` | 3.0 | 192 |

## Application Lifecycle (`lifecycle.py`)

`AppLifecycleManager` enforces single-instance execution (Windows named mutex)
and manages the session engine subprocess:

- `ensure_single_instance()` -- returns False if another instance holds the mutex
- `launch_daemon()` -- spawns `session_engine.py` as a subprocess with stdin pipe for IPC
- `shutdown()` -- graceful terminate with 3-second timeout, then force kill

Registered as an `atexit` handler to guarantee cleanup on process exit.

## Integration Points

```
main.py ──> lifecycle.launch_daemon() ──> session_engine.run_session_loop()
                                              |
                                              +──> config.DATABASE_URL
                                              +──> config.get_setting()
                                              +──> spatial_data.get_map_metadata()
                                              +──> constants.TICK_RATE
```

## Development Notes

- **Config globals are stale in daemon threads.** Always use `get_setting()` or
  `get_credential()` in background threads. Module-level imports capture a snapshot
  that is never updated unless `refresh_settings()` runs.
- **Never hardcode match data paths.** Use `config.MATCH_DATA_PATH` which resolves
  dynamically based on `PRO_DEMO_PATH` availability.
- **Spatial data supports hot reload.** Call `reload_spatial_config()` to force
  re-reading `map_config.json` without restarting the application.
- **Z-axis matters.** Multi-level maps (Nuke, Vertigo) require `get_map_metadata_for_z()`
  instead of plain `get_map_metadata()` for correct level selection.
- **The session engine monitors stdin.** If the parent process dies (pipe closes),
  all daemons shut down automatically. Sending "STOP" on stdin triggers graceful exit.
