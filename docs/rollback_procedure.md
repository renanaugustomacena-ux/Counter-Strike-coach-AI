# Rollback procedure — Data Restoration Plan v3

If any phase of the v3 restoration corrupts `database.db` or
`hltv_metadata.db`, this procedure reverts both DBs to the
2026-05-03 pre-restoration baseline.

## Pre-flight verified

- Backup created via online-safe `sqlite3 .backup` (not file copy).
- Byte-identical to live DB at backup time:
  `pre-restoration-2026-05-03.db` = 1,529,974,784 B
  `pre-restoration-2026-05-03.hltv_metadata.db` = 45,056 B
- Row-count parity verified across 7 tables (playertickstate=3,908,990;
  playermatchstats=2,040; ingestiontask=65; coachinginsight=2;
  matchresult=0; roundstats=0; mapveto=0).
- Dry-run rollback to `/tmp/test_restore.db` reproduced full row-count
  parity on 2026-05-03; procedure validated end-to-end.

## Steps

```bash
# 1. Stop services (D-track tools, HLTV daemon, Qt app)
pkill -f hltv_sync_service || true
pkill -f Programma_CS2_RENAN.apps.qt_app.app || true

# 2. Acquire rollback lock so no concurrent writer can race
./.venv/bin/python -c "from Programma_CS2_RENAN.core import lock_files; lock_files.acquire('rollback')"

# 3. Restore main DB
cp Programma_CS2_RENAN/backups/pre-restoration-2026-05-03.db \
   Programma_CS2_RENAN/backend/storage/database.db
sqlite3 Programma_CS2_RENAN/backend/storage/database.db \
   "PRAGMA wal_checkpoint(TRUNCATE);"

# 4. Restore HLTV DB
cp Programma_CS2_RENAN/backups/pre-restoration-2026-05-03.hltv_metadata.db \
   Programma_CS2_RENAN/backend/storage/hltv_metadata.db
sqlite3 Programma_CS2_RENAN/backend/storage/hltv_metadata.db \
   "PRAGMA wal_checkpoint(TRUNCATE);"

# 5. Verify row-count parity against the baseline JSON
./.venv/bin/python - <<'PY'
import json, sqlite3
baseline = json.load(open('docs/restoration_baseline_2026-05-03.json'))
con = sqlite3.connect('file:Programma_CS2_RENAN/backend/storage/database.db?mode=ro', uri=True)
for tbl, expected in baseline['main_db']['tables'].items():
    actual = con.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()[0]
    assert actual == expected, f'{tbl}: live={actual} baseline={expected}'
print('main DB parity: OK')
PY

# 6. Run validator to confirm code/data alignment
./.venv/bin/python tools/headless_validator.py

# 7. Release the rollback lock
./.venv/bin/python -c "from Programma_CS2_RENAN.core import lock_files; lock_files.release('rollback')"
```

## When to use

- A D-track aggregator produces obviously-broken data
  (e.g., negative kill counts, KAST > 1, invalid `data_quality` values).
- An H-track scraper writes malformed `detailed_stats_json` that
  fails the 8 KB cap or breaks `pro_comparison_vm` reads.
- An Alembic migration runs partially and the schema is in a
  mid-state nobody can describe in plain language.
- Any phase corrupts the WAL such that `PRAGMA integrity_check`
  reports anything other than `ok`.

## When NOT to use

- A specific row has a wrong value but the schema is intact —
  fix the row directly via UPDATE; rollback is heavyweight.
- A new tool errors out on its first run — the tool doesn't run,
  the DB isn't touched, no rollback needed.
- A pre-commit hook reformats files — that's a working-tree state,
  not a DB state; rollback doesn't apply.

## After rollback

1. Document what triggered the rollback in `AUDIT.md` with a UTC
   ISO 8601 timestamp.
2. Investigate root cause before re-attempting the failed phase.
3. If the failed phase needs a code fix, ship the fix on a separate
   branch with a regression test before re-running.

The backup files in `Programma_CS2_RENAN/backups/pre-restoration-*`
are gitignored. Do not delete them until V phase passes and the
restoration is signed off.
