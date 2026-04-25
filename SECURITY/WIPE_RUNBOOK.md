# Wipe-Tooling Runbook — `tools/wipe_for_reingest_safe.py`

**Version:** 1.0
**Date:** 2026-04-25
**Owner:** Renan Augusto Macena

> *"Destructive actions need explicit confirmation."* This SOP governs every database wipe.

---

## 0. Background

The project went through 4 iterations of wipe tooling (`wipe_for_reingest.py`, `_v2.py`, `_v3.py`,
`_v4.py`) during a 2026-Q1 re-ingestion campaign. v4 evolved a sound atomic strategy
(swap `live.db` → `live.db.OLD`, build `.fresh` alongside, migrate keep-data) but never gained:
- a confirmation flag
- a default dry-run
- a DB-unlock check
- an audit-log entry
- a forensic snapshot

**Phase 1 deliverable:** introduce `tools/wipe_for_reingest_safe.py` with all five guards. v1–v4 stay
in operator ownership and are not removed during the live ingestion. After ingestion completes,
v1–v4 should be deleted (untracked files; not in git history).

---

## 1. When to wipe

| Trigger | Wipe? | Notes |
|---|---|---|
| Schema migration that re-shapes feature columns | Yes | After `alembic` migration; before re-ingest |
| Data quality bug discovered after ingest | Yes | Wipe affected tables only |
| Routine "fresh state" before testing | **No** | Use a separate dev DB, not the production monolith |
| Operator suspects corruption | **No, first** | Run `IR-03` first — restore from backup if possible |
| Disk space recovery | No | Use SQLite `VACUUM` / WAL checkpoint |

The wipe tool deletes rows from these tables (verified against v4 hardcoded list):
- `playermatchstats`
- `playertickstate`
- `roundstats`
- `coachinginsight`
- `ingestiontask`

Other tables are preserved.

---

## 2. Pre-flight checklist

Before invoking the wipe tool:

- [ ] Confirm the operator (`whoami` / `echo $USER`) matches the expected production owner.
- [ ] Confirm UTC timestamp; record in operations log.
- [ ] Confirm no daemons running:
  ```
  pgrep -f run_ingestion.py
  pgrep -f run_worker.py
  pgrep -f hltv_sync_service.py
  ```
- [ ] Confirm `database.db` is not locked:
  ```
  fuser Programma_CS2_RENAN/backend/storage/database.db 2>/dev/null
  ```
  (no output = no holders)
- [ ] Confirm latest backup exists in `Programma_CS2_RENAN/backups/`.
- [ ] Confirm `CS2_WIPE_SNAPSHOT_KEY` is set (env var or keyring).

---

## 3. Standard procedure

### 3.1 Dry-run first (always)

```
python tools/wipe_for_reingest_safe.py
```

(no flags = dry-run). Output:
- The tables it would wipe
- The row counts it would remove
- The byte size it would reclaim
- The exact SQL it would execute
- Whether all pre-flight checks pass

Dry-run **never modifies** the database.

### 3.2 Snapshot

```
python tools/wipe_for_reingest_safe.py --snapshot
```

Creates an HMAC-sealed Fernet-encrypted tarball at:
```
Programma_CS2_RENAN/backups/wipe_snapshots/<UTC_TS>/snapshot.tar.gz.fer
```

Snapshot contains `database.db` + `database.db-wal` + `database.db-shm`. Encrypted with the key
derived from `CS2_WIPE_SNAPSHOT_KEY`. Retention: 30 days (operator manually purges older).

### 3.3 Execute

```
python tools/wipe_for_reingest_safe.py --confirm-wipe
```

The tool refuses to execute without `--confirm-wipe`. With both `--snapshot` and `--confirm-wipe`,
it snapshots first, then wipes.

### 3.4 Verify

```
sqlite3 Programma_CS2_RENAN/backend/storage/database.db <<'EOF'
SELECT 'playermatchstats', COUNT(*) FROM playermatchstats
UNION ALL SELECT 'playertickstate', COUNT(*) FROM playertickstate
UNION ALL SELECT 'roundstats', COUNT(*) FROM roundstats
UNION ALL SELECT 'coachinginsight', COUNT(*) FROM coachinginsight
UNION ALL SELECT 'ingestiontask', COUNT(*) FROM ingestiontask;
EOF
```

All five counts should be 0.

### 3.5 Audit log

Wipe events appear in `audit.log` (Phase 2) as:
```json
{"event_type": "wipe_invoked", "fields": {"operator": "...", "tables": [...], "row_counts": {...}, "snapshot_path": "...", "outcome": "success"}, ...}
```

Verify with `python goliath.py audit verify` (after Phase 2).

---

## 4. Restore from snapshot

If the wipe was a mistake:

```
python tools/wipe_for_reingest_safe.py --restore --snapshot-path Programma_CS2_RENAN/backups/wipe_snapshots/<UTC_TS>/snapshot.tar.gz.fer
```

Requires `CS2_WIPE_SNAPSHOT_KEY` matching the key used at snapshot time. Restore is also gated by
a confirmation prompt and writes an audit-log `wipe_restored` event.

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| Operator forgets `--snapshot` and wipes irrecoverably | Dry-run default; tool prints "Snapshot was NOT taken" warning when proceeding without `--snapshot` |
| Operator runs against wrong DB path | Default path resolved via `core/config.py`; explicit `--db-path` required for non-default |
| `CS2_WIPE_SNAPSHOT_KEY` is lost — snapshots unreadable | Documented in this SOP; key should be stored in operator's password manager |
| DB locked at wipe time → corruption | Pre-flight check refuses to proceed |
| Audit log not written (audit subsystem broken) | Wipe tool warns and asks for explicit `--ignore-audit-failure` |

---

## 6. Operational notes

- The legacy v4 logic (atomic swap with `.fresh` and `.OLD`) is preserved as one of the available
  modes (`--mode swap`). The default mode (`--mode rows`) issues `DELETE FROM` per table for the
  small wipe lists; `swap` is for catastrophic full-DB reset.
- After a successful wipe, run `python tools/headless_validator.py` to confirm system health.
- The 30-day snapshot retention is a guideline, not enforced. Operator may purge sooner with
  `--purge-snapshots-older-than <days>`.

---

## 7. References

- **ISO/IEC 27001:2022** A.8.13 (Information backup), A.8.10 (Information deletion)
- **NIST SP 800-88 r1** Guidelines for Media Sanitization
- **Doctrine §57** Least Privilege Everywhere
