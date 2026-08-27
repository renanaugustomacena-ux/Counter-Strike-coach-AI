# Cluster 01 — Entry Points & Launchers

Files read (full): `console.py` (1671), `goliath.py` (300), `batch_ingest.py` (324),
`run_full_training_cycle.py` (289), `schema.py` (324), `setup.py` (5),
`Programma_CS2_RENAN/run_ingestion.py` (1670), `run_worker.py` (194),
`hltv_sync_service.py` (274), `Programma_CS2_RENAN/__init__.py`,
`Programma_CS2_RENAN/migrations/env.py` (deprecated tombstone),
shell: `ingest.sh`, `launch.sh`, `train.sh`, `train_docker.sh`, `_rocm_smoke.sh`,
`export_env.bat`, `setup_new_pc.bat`, `scripts/Setup_Macena_CS2.ps1`,
`scripts/build_exe.bat`, `scripts/build_production.bat`, `scripts/reaggregate.sh`.

## Purpose map

| Entry | Role |
|---|---|
| `console.py` | Unified TUI/CLI console v3.0 — command registry (ml/ingest/build/test/sys/set/svc/maint/tool), lazy backend via `backend/control/console.get_console()`, Rich Live dashboard + StatusPoller thread |
| `goliath.py` | Batch orchestrator for build/sanitize/integrity/audit/db/doctor/baseline subsystems (subprocess + direct imports) |
| `batch_ingest.py` | Parallel pro-demo ingestion via ProcessPoolExecutor (`max_tasks_per_child=1` on 3.11+ against DataFrame leaks); RAM-based worker autosize (~6GB/worker); optional auto-train after ingest |
| `run_full_training_cycle.py` | THE training entry: seeds (DET-01 `set_global_seed`), builds callback registry (TensorBoard + MaturityObservatory + EmbeddingProjector), runs TrainingOrchestrator for JEPA then RAP, pre/post eval via `tools/eval_harness.py` subprocess (B6.1), exit 3 on aborted phase (F-0043) |
| `schema.py` | Standalone sqlite3 DB suite: inspect/migrate/import/fix/reset with identifier validation; complementary to Alembic, hot-patch oriented |
| `run_ingestion.py` | Core ingestion pipeline (see below) — most important file of this cluster |
| `run_worker.py` | Daemon: atomic task claim loop + stale-task recovery (ZOMBIE_TASK_THRESHOLD_SECONDS=1800, F-0015), stop via `hltv_sync.stop` file |
| `hltv_sync_service.py` | HLTV stats scraper daemon: FlareSolverr (Docker) for Cloudflare, 7d full / 24h incremental cadence, dormant 6h when blocked, PID+stop-file lifecycle |

## Ingestion data path (verified in run_ingestion.py)

1. `process_new_demos` → `refresh_settings()` → StorageManager scan → queue `IngestionTask` rows.
2. `process_queued_tasks` → **atomic claim** via conditional `UPDATE ... WHERE status='queued'` (F-0037; run_ingestion.py:356-369) — six concurrent runner types exist (home screen, settings, console, batch_ingest, ingest_pro_demos, run_worker).
3. `_ingest_single_demo` (run_ingestion.py:460):
   - `parse_demo` → aggregate per-player stats → NaN/Inf sanitize (R3-H09), rating clamp [0,5];
   - OI-2 `match_date_resolver.resolve_match_date` with provenance marker;
   - `persist_round_stats_and_enrichment` (F6-19: RoundStats written at ingest, not only by tools);
   - `_save_sequential_data`: `parse_sequential_ticks(ALL players)` → `_interpolate_position` (alive-segment-bounded linear interp; circular sin/cos for yaw/pitch; (0,0,0) counted as data-quality signal R4-14-01) → `enrich_tick_data` (cross-player features, real header tick_rate GAP-01, range [32,256]) → **dual write**: per-match `matchtickstate` shard (match_id = sha256(stem) mod 2^63-1, DA-03-01) + monolith `playertickstate`, chunked to_sql (~15-20s vs 736s ORM loop).
   - `_EventExtractor`: 9 event families (weapon_fire, player_hurt, player_death, smoke/molotov pairs, flash/HE detonate, grenade_thrown GAP-02 with tick-state origin, bomb) with per-(tick,player) MultiIndex state lookup ±5 tick fallback.
   - `_finalize_match_record`: metadata incl. per-demo tick_rate; `match_complete=1` set only AFTER ticks+events land (P4-A — Teacher daemon must never train on half-written matches).
4. `run_ml_pipeline` (coaching inference; NOT on ingest hot path): SkillLatentModel vector → curriculum level → level-conditioned RAP inference over 5 windows → CoachingInsight rows via ExplanationGenerator ("Silence is a Valid Action" — no message = no insight row).

## Invariants observed (candidate doctrine material)

- **Tick decimation FORBIDDEN** — stated twice (run_ingestion.py:1306, 1431); every parsed row maps 1:1 to a stored row.
- **DB-boundary isolation**: ingestion never reads `hltv_metadata.db`; pro-baseline Z-scores computed only at coaching inference (run_ingestion.py:127-131, 563-589).
- **Atomicity via SQL, not app locks**: task claims are conditional UPDATEs; state rows are the single source of truth; final status flip guaranteed in `finally:` (batch_ingest.py:97-119 — the Apr 2026 "0 failed after 301 failures" lesson).
- **Determinism**: every training entry must call `set_global_seed()` (DET-01/REFERENCE §3); per-epoch subsample rotation anchored at GLOBAL_SEED+epoch (B1.3) so probe seeds vary init, not data.
- **Honest exit codes**: aborted training phase exits 3, not 0 (F-0043); `[error]` first line → exit 1 in console CLI.
- **(0,0,0) positions poison training** — never interpolated into validity; NaN preferred, counted, warned.
- **Real tick_rate over assumed 64.0** (GAP-01) — hardcoding halved time_in_round on 128-tick demos.
- **Two-phase data ambition**: `is_blinded` derived from `flash_duration > 0` (CS2 removed legacy signal) OR legacy value for old demos — sensor-truth over schema-truth.
- Per-process log roles (`CS2_LOG_ROLE`) set only under `__main__` — imports must not flip the importer's role (F-0011).

## Risks / open questions carried forward

- `console.py` `_cmd_test_all` runs pytest with `-x -q` timeout 300s — full suite is 163 files; likely slower in practice (check local gate recipe).
- `schema.py` duplicates migration responsibility with Alembic (`alembic/` root is canonical; Programma migrations/env.py is a tombstone that raises).
- `run_worker.py` `_fetch_next_task_data` claim is select-then-update in one session (R3-M25) — weaker than F-0037 conditional UPDATE used in run_ingestion; SQLite serialization likely saves it, but the two claim styles coexist.
- `train_docker.sh` references ROCm RX 9070 XT; `run_full_training_cycle` mentions GTX 1650 4GB — two GPU profiles in play.
- `scripts/build_production.bat` still checks `import kivymd` — Kivy legacy in the dependency preflight despite PySide6 migration (candidate phantom ref; per repo rule, repoint not delete).
