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

mkdir -p logs
TS=$(date +%Y%m%d_%H%M%S)
LOG="logs/ingest_${TS}.log"

# Rewrite short flags. All three short options take a value argument.
args=()
while [ $# -gt 0 ]; do
    case "$1" in
        -w) args+=(--workers "$2"); shift 2 ;;
        -l) args+=(--limit "$2"); shift 2 ;;
        -D) args+=(--demo-dir "$2"); shift 2 ;;
        *)  args+=("$1"); shift ;;
    esac
done

echo "Ingestion starting — log: $LOG"
echo "Tail with: tail -f '$LOG'"
echo "----------------------------------------"

"$VENV_PYTHON" batch_ingest.py --no-train "${args[@]}" 2>&1 | tee "$LOG"
RC=${PIPESTATUS[0]}

echo "----------------------------------------"
echo "Ingestion finished (exit $RC). Log archived at $LOG"
exit "$RC"
