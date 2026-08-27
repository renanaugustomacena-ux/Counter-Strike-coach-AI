# Cluster 02 — `core/`

Files read (all 19): session_engine, config, localization, spatial_data, map_callouts,
asset_manager, lock_files, playback_engine, lifecycle, demo_frame, app_types,
map_manager, spatial_engine, tick_rate, known_maps, registry, constants, frozen_hook, __init__.

## Purpose map

| File | Role |
|---|---|
| `session_engine.py` | The daemon supervisor: 4 threads — Scanner (FS→queue), Digester (queue→stats, 1 task/cycle for shutdown responsiveness), Teacher (retrain trigger → `CoachTrainingManager.run_full_cycle()`), Pulse (heartbeat 5s) — plus 30s watchdog that restarts dead daemons. Parent-death detection via stdin EOF. |
| `config.py` | Settings SSOT: `user_settings.json` + `.env` loader (CFG-ENV-01) + keyring secrets. Thread-safe via RLock; `refresh_settings()` for daemons. Feature flags: USE_JEPA_MODEL, USE_RAP_MODEL, USE_COPER_COACHING (default True), USE_HYBRID/OLLAMA/RAG (default False), USE_POV_TENSORS. |
| `tick_rate.py` | **26-NORM-01 SSOT** — only module allowed to spell 64. Resolution: shard metadata → header → `None` (honest sentinel, never fabricated). Out-of-range [32,256] rejected loudly, not clamped. Guarded by `test_tick_rate_ssot.py`. |
| `known_maps.py` | map-SSOT (CP0 #2): one frozenset for 11 maps; Pass 1 had found TWELVE divergent lists. Longest-first regex for filename sniffing. |
| `spatial_data.py` | World↔radar transforms per map (pos_x/pos_y/scale), multi-level Z support (Nuke z_cutoff=-495, Vertigo 11700), `compute_z_penalty` normalized [0,1] for NN supervision. Landmarks DERIVED from map_callouts at load (R4: two sources can never diverge again). |
| `map_callouts.py` | WR-77 canonical callout source: ~160 NamedPositions across 9 maps, nearest-neighbor lookup ≤600u, "unknown area" honest fallback. |
| `lock_files.py` | Repo-root `.locks/` named locks: atomic O_CREAT\|O_EXCL acquire, dead-PID reclaim via atomic os.replace steal, Windows liveness via GetExitCodeProcess (26-WIN-02), foreign-lock release protection (F-0009), signal handlers release-then-reraise. |
| `lifecycle.py` | Single-instance (Win mutex / POSIX named lock, fail-closed both ways) + session_engine daemon Popen with stdin pipe as life-line. |
| `demo_frame.py` / `app_types.py` | Frame dataclasses (PlayerState sanitizes non-finite x/y/z/yaw in __post_init__, DF-01) vs numeric enums. TWO Team enums by design (string parser-side, numeric DB/UI-side) with AT-01 fail-fast cross-enum `__eq__` and explicit bridge `team_from_demo_frame`. |
| `playback_engine.py` | Frame playback + interpolation; `load_frames` REQUIRES tick_rate (no default — 26-TICK); circular angle interp with non-finite guard (Inf used to hang the UI clock). |
| `asset_manager.py` / `map_manager.py` / `registry.py` / `localization.py` | UI-support: AssetAuthority singleton with magenta-checker fallback ("clearly missing, not false data"); Kivy imports quarantined behind try/except (C11) — Qt is the live UI, Kivy paths degrade loudly. i18n en/pt/it, JSON-first with hardcoded fallback chain. |
| `constants.py` | Seconds-only temporal constants (smoke 18s, molotov 7s, flash 2s, trade window 3s, memory tau 2.5s cutoff 7.5s). Import-time seconds→ticks derivations were REMOVED (26-TICK: "tick windows MUST be computed at point of use from the per-demo rate"). |
| `spatial_engine.py` | Static world↔pixel transforms; unknown map → (0.5,0.5) explicitly labeled a FABRICATED center with once-per-map warning. |
| `frozen_hook.py` | PyInstaller freeze support + cwd stabilization. |

## Teacher retraining trigger (session_engine.py:566-597)

- Cold start: requires ≥10 pro samples (R4: the growth test `>= last*1.10` was vacuous at last=0).
- Steady state: retrain when pro_count grows ≥10% since last trained count.
- Sample count committed only AFTER successful training; CoachState row created if missing (R4: silent no-op caused infinite cold-start retrain loop).
- Training mutual exclusion with console via `ml_controller._TRAINING_LOCK` (NN-02).
- Post-retrain: belief calibration (G-07, `AdaptiveBeliefCalibrator.auto_calibrate` on death events) and meta-shift detection (Proposal 11, `TemporalBaselineDecay.detect_meta_shift`).

## Invariants observed (doctrine candidates)

- **Tick rate is per-demo, never assumed** — "il supremo invariante". None > fabricated default; the explicit DEFAULT_TICK_RATE import is the audit trail.
- **Anti-fabrication as a stated value**: fabricated fallbacks are labeled as such in code and logged (spatial center, checkered texture, honest-NULL match_date in cluster 01).
- **SSOT discipline**: tick rate, known maps, callouts, landmarks each have exactly one authority; derived copies are generated, not hand-maintained.
- **Fail-closed protection of the DB**: single-instance guards return False on ANY doubt; two instances = concurrent SQLite writers.
- **Seconds in constants, ticks at point of use.**
- **Daemons are supervised, event-driven, and shutdown-responsive**: watchdog restart, `_shutdown_event.wait()` instead of sleeps, 1-task digester cycles.
- **Core DB always in-project; BRAIN_DATA_ROOT only holds regeneratable artifacts** (models/logs/runs) — changing it can never lose raw training data. $HOME is never an acceptable data root (F-0008).
- **Settings written atomically** (tmp + os.replace), secrets to OS keyring with plaintext-0600 fallback, mask sentinel never returned to callers.

## Risks / open questions carried forward

- ZOMBIE_TASK_THRESHOLD_SECONDS default is 1800 in session_engine/run_worker but **300 in config.py defaults** (config.py:238) — config default contradicts the P4-B lesson ("5 minutes was THE duplicate-processing bug"). Check who wins at runtime (get_setting returns 300 default → run_worker overrides its own default only when setting missing... actually setting IS present in defaults, so 300 wins). **Likely real bug.**
- Scanner daemon gates on `state.hltv_status == "Scanning"` — ingestion active-state coupling to an "hltv" field name; verify semantics in state_manager.
- `MIN_DEMOS_FOR_COACHING = 1` (config.py:289) — the profile-ready gate is minimal.
- localization retains f-string-built dict entries at import (home dir baked in at import time; JSON path re-evaluates at load).
