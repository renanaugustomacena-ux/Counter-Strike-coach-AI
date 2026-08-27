# Cluster 04 — `backend/storage/` + schema + alembic

Files read (all): db_models, database, match_data_manager, storage_manager, state_manager,
backup_manager, db_backup, db_migrate, stat_aggregator, maintenance, remote_file_server,
alembic/env.py + all 20 version files, backend/storage/migrations (deprecated chain, env + 2 versions).

## Three-tier storage architecture (the data doctrine's backbone)

- **Tier 1-2 — Monolith `database.db`** (always in-project): all long-lived tables. WAL mode, pool_size=1 single-writer, busy_timeout 30s, FK pragma ON (DB-06 — "schema FKs are decorative without it"), wal_autocheckpoint 512 (DB-07).
- **Tier 3 — per-match shards** `match_data/match_{id}.db` where id = sha256(demo_stem) mod 2^63-1: `matchtickstate` (~1.7M rows/match, "Telemetry Cliff" solution), `match_event_state`, `match_metadata` (per-demo tick_rate, match_complete flag). LRU engine cache (50). Per-shard schema versioning (v3) with typed migration registry and identifier/type/default allowlists before any DDL f-string (DB-01).
- **`hltv_metadata.db`** — completely separate DB for Pro* tables; separation principle: "HLTV scrapes provide pro stats only; demo-derived data never crosses into hltv_metadata.db". Its table registry `_HLTV_TABLES` is contract-tested — a Pro* model missing from the list gets DROPPED as orphan (the R4-CRIT Phase-H1 data-loss lesson, database.py:79-94). Schema reconciliation (#47/GAP-14): additive drift → ALTER in place; non-additive → RENAME to *_stale_<ts> (data preserved), never silent drop.

## Model layer highlights (db_models.py)

- `PlayerMatchStats`: per-player-per-demo aggregates + HLTV2.0 components + trade/enrichment/utility fields; UNIQUE(demo,player); CHECKs (rating 0-5); `dataset_split` enum (train/val/test/unassigned) + `match_date_source` provenance (OI-2); legacy float data_quality coerced to labels.
- `PlayerTickState` (monolith legacy ticks): enriched context columns; composite POV index (demo,player,tick) added by migration e5f6a7b8c9d0 for JEPA window fetching (~4.5k window queries/epoch — R4 CRIT perf fix on ~429M rows).
- `MatchTickState` (shard): bound to legacy table name `matchtickstate` — the POV-RAP-FIX lesson: ORM briefly pointed at `match_tick_state` (modern name), an EMPTY parallel table, "silently dropping every RAP training batch". id maps to SQLite rowid.
- `MatchEventState`: player POV events; "the coach learns from SITUATIONS, not identities — NO steamid"; entity_id sentinel -1 = unpopulated (no false pairing via default 0); `duration_estimated` flag → lower training weight (P3-B).
- `CoachingExperience` (COPER experience bank): context_hash, game_state_json (16KB cap + JSON validity), action/outcome/delta_win_prob, 384-dim embedding, `strategy_label` (GAP-09, taxonomy in docs/strategy_taxonomy.md), feedback loop (times_advice_given/followed, effectiveness) and **TrueSkill uncertainty (mu_skill, sigma_skill)** with pessimistic `confidence_score = mu - kappa*sigma` (KT-01).
- `RoundStats`: per-round isolation layer (Proposal 4) — data flow raw ticks → RoundStats → PlayerMatchStats; UNIQUE(demo,round,player); the source of G-01 concept labels.
- `CoachState`: singleton (CHECK id=1) live pipeline state incl. triple-daemon statuses, training telemetry, heartbeat.
- `DataLineage` (P5-D, append-only provenance) + `DataQualityMetric` (P5-E, per-run metrics) — auditability tables.
- `TacticalKnowledge`: RAG entries with JSON-encoded 384-dim embeddings in SQLite.
- WR-76: legacy demo_name suffix regex shared (`MATCH_STATS_DEMO_SUFFIX_RE`) — "do NOT redefine locally".

## Managers

- `database.py`: singleton managers (double-checked locks; direct instantiation forbidden by repo invariant); `_add_missing_columns` self-healing additive schema evolution with type allowlist (DB-04) and proper SQL literal quoting; PlayerMatchStats upsert via native `ON CONFLICT DO UPDATE` (TOCTOU-free); `delete_match_cascade` (P5-A) FK-ordered; `detect_orphans` (P5-B).
- `match_data_manager.py`: dangling shard symlink ⇒ `MatchDataUnavailableError` with recovery instructions — "positive evidence that storage is unreachable... a condition to report, not a cue to invent empty storage" (the anti-fabrication principle applied to storage). WR-14 device-ID check blocks writes after drive disconnect. `warn_if_shards_in_legacy_location` reports and never relocates (the 2026-07-26 disk-fill lesson: relocation must be explicit). Memory window in SECONDS converted per-demo (26-TICK).
- `state_manager.py`: DAO for CoachState with typed DaemonName enum (unknown daemon raises — silent no-op masked state transitions), telemetry failure escalation (SM-02), notification auto-prune at 500 (SM-03), DB-05 generic error detail to UI (SQL paths never leak).
- `backup_manager.py` / `db_backup.py`: SQLite Online Backup API (no SQL string, injection-free, WAL-safe), integrity check on the backup then delete-on-fail; size ceiling 50GiB + free-space margin (ST-BK-01/measured 2026-07-17 disk-fill incident); retention 7 daily + 4 weekly (ISO-year-aware); shard backup raises on ANY failed shard — "a partial archive must never masquerade as a complete backup"; restore checkpoints WAL first, keeps rollback copy, deletes stale WAL/SHM (STOR-01).
- `storage_manager.py`: ingest/archive dirs with OI-8/F-0008 never-$HOME defaults (managed DATA_DIR/demos); quota measures only *.dem files (R4: whole-tree vs $HOME false-positive); `list_new_demos` dedups by task path AND stats stem, excludes `ingested/` subtree; archive is best-effort by contract (DB dedup is the real guard).
- `remote_file_server.py`: FastAPI demo server — token auth (hmac.compare_digest), per-IP rate limit, path traversal via is_relative_to, refuses non-localhost bind without TLS (BE-07) unless explicit env override; settings resolved per-request (daemon config rule: rotation without restart).
- `db_migrate.py`: startup auto-upgrade via Alembic; `CS2_ALEMBIC_URL` env for throwaway verification DBs.
- `stat_aggregator.py`: HLTV spider → ProPlayer/StatCard; **ratio-normalization boundary** (V-2): values >1.0 treated as percentages ÷100 — system standard is ratio [0,1]; JSON size guard truncates to core stats (S-07).
- `maintenance.py`: tick pruning by age, chunked IN() under SQLite's 999-var limit.

## Alembic

Canonical chain at root `alembic/` (20 revisions, f769fbe67229 → a7b8c9d0e1f2); env.py imports every model explicitly ("no-dead-code — imports register metadata"), auto pre-migration backup. All recent migrations: additive-only, idempotent `_column_exists` guards, identifier whitelists (DB-02), and index-after-bulk-load ETL discipline (steamid D1). f6a7b8c9d0e1 documents "schema honesty": dead never-written columns get DROPPED rather than left implying a feature exists. Two deprecated chains raise RuntimeError tombstones (replace-not-delete rule).

## Invariants observed (doctrine candidates)

- **One writer per SQLite file; contention eliminated by separation** (monolith / hltv / per-match shards), not by locks in app code.
- **Schema evolution is additive and idempotent**; destructive change requires preserving data under a stale name. Explicit table registries are load-bearing (absence ⇒ dropped as orphan) and contract-tested.
- **The ORM must point where the data actually lives** — table-name drift silently starves training (POV-RAP-FIX); realignment over rewrite.
- **Storage unreachability is an error to surface, never a state to paper over with empty dirs** (symlink doctrine, WR-14 device check).
- **Backups: verified or refused** — integrity-checked, size/space-guarded, partial ⇒ exception.
- **match_id derivation (sha256 mod 2^63-1) is a cross-file contract** with exactly one helper (`demo_name_to_match_id`).
- **Ratios are [0,1] system-wide**; >1.0 at a boundary means percentage and is normalized at that boundary.
- **Events carry no identity beyond intra-match names** — the coach learns situations, not players (privacy + generalization stance).

## Risks / open questions carried forward

- `maintenance.prune_old_metadata` deletes PlayerTickState for demos older than 30 days by processed_at — potentially at odds with JEPA training that reads monolith ticks; check who calls it (candidate dead/dangerous tool).
- CoachState.status stored via raw String column with enum-value default — update_status("global") validates against enum values; other daemon statuses are free strings.
- storage_manager quota archiving moves user demos to archive when >10GB — interacts with list_new_demos exclusion ("ingested" only, archive dir is elsewhere) — appears consistent but verify archive_dir not rescanned.
- remote_file_server default archive path "D:/CS2_Demos/Archive" (Windows-specific literal default).
