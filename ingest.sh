#!/bin/bash
# Macena CS2 Analyzer — one-shot pro-demo ingestion.
#
# Parses every .dem under PRO_DEMO_PATH that is not yet in PlayerMatchStats.
# Does NOT chain into training — run train.sh afterwards when you want that.
#
# Usage:
#   ./ingest.sh                            # ingest all new demos, auto-sized workers
#   ./ingest.sh -w 4 | --workers 4         # pin worker count
#   ./ingest.sh -l 10 | --limit 10         # smoke test: first 10 pending
#   ./ingest.sh -D /path | --demo-dir /path   # override PRO_DEMO_PATH
#   ./ingest.sh -v | --verbose             # CS2_LOG_LEVEL=DEBUG (per-stage detail)
#   ./ingest.sh --show-status              # print IngestionTask counts and exit
#
# Short flags are rewritten to canonical long forms before forwarding to
# batch_ingest.py. --no-train is enforced unconditionally (batch_ingest.py
# will log a line noting the skip); run train.sh afterwards when training.
set -e
cd "$(dirname "$0")"

VENV_PYTHON="$HOME/.venvs/cs2analyzer/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
    echo "ERROR: venv not found at $VENV_PYTHON" >&2
    echo "Create it with: python3.10 -m venv ~/.venvs/cs2analyzer" >&2
    exit 1
fi

# --show-status: read-only snapshot of IngestionTask, then exit.
# Handled before log-file setup so it never creates an empty logs/ entry.
if [ "$1" = "--show-status" ]; then
    exec "$VENV_PYTHON" - <<'PY'
import sqlite3, sys
from pathlib import Path
db = Path(__file__).resolve().parent / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db"
if not db.is_file():
    print(f"DB not found: {db}", file=sys.stderr); sys.exit(1)
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
total = 0
for status in ("queued", "processing", "completed", "failed"):
    n = con.execute("SELECT COUNT(*) FROM ingestiontask WHERE status=?", (status,)).fetchone()[0]
    print(f"{status:>11}: {n}")
    total += n
print(f"{'total':>11}: {total}")
n_stats = con.execute("SELECT COUNT(DISTINCT demo_name) FROM playermatchstats").fetchone()[0]
print(f"{'in stats':>11}: {n_stats} (distinct demo_name in PlayerMatchStats)")
PY
fi

mkdir -p logs
TS=$(date +%Y%m%d_%H%M%S)
LOG="logs/ingest_${TS}.log"

# Rewrite short flags. -w/-l/-D take a value; -v/--verbose is a switch
# consumed locally (sets CS2_LOG_LEVEL, not forwarded to batch_ingest.py).
args=()
while [ $# -gt 0 ]; do
    case "$1" in
        -w) args+=(--workers "$2"); shift 2 ;;
        -l) args+=(--limit "$2"); shift 2 ;;
        -D) args+=(--demo-dir "$2"); shift 2 ;;
        -v|--verbose) export CS2_LOG_LEVEL=DEBUG; shift ;;
        *)  args+=("$1"); shift ;;
    esac
done

echo "Ingestion starting — log: $LOG"
echo "Tail with: tail -f '$LOG'"
echo "Status:    ./ingest.sh --show-status (in another terminal)"
if [ -n "${CS2_LOG_LEVEL:-}" ]; then
    echo "Log level: CS2_LOG_LEVEL=$CS2_LOG_LEVEL"
fi
echo "----------------------------------------"

"$VENV_PYTHON" batch_ingest.py --no-train "${args[@]}" 2>&1 | tee "$LOG"
RC=${PIPESTATUS[0]}

echo "----------------------------------------"
echo "Ingestion finished (exit $RC). Log archived at $LOG"
exit "$RC"
