#!/bin/bash
# Macena CS2 Analyzer — full-cycle AI training.
#
# Runs run_full_training_cycle.py across every architecture enabled in
# user_settings.json:
#   - JEPA   (USE_JEPA_MODEL, always)
#   - RAP    (USE_RAP_MODEL, soft-gated by coach_manager.check_maturity_gate — 50 demos)
# Checkpoints land in Programma_CS2_RENAN/models/.
# TensorBoard events land in Programma_CS2_RENAN/runs/ (see RUNS_DIR in config).
#
# Env overrides:
#   EPOCHS=30 ./train.sh                 # cap at 30 epochs instead of 100
#   MODEL_TYPE=jepa ./train.sh           # JEPA only (skip RAP)
#
# Usage:
#   ./train.sh                           # all models, default 100 epochs
#   ./train.sh -d | --dry-run            # 1-epoch smoke test
#   ./train.sh -r | --resume             # resume from latest checkpoint
#   ./train.sh -e 30 | --epochs 30       # cap epochs (overrides env)
#   ./train.sh -m jepa | --model-type jepa   # pick a model subset
#   ./train.sh -t PATH | --tb-logdir PATH    # TensorBoard log directory
#   ./train.sh -T | --no-tensorboard     # disable TensorBoard
#
# Short flags are rewritten to the canonical long form before forwarding to
# run_full_training_cycle.py (whose argparse only declares long options).
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
LOG="logs/train_${TS}.log"

EPOCHS="${EPOCHS:-100}"
MODEL_TYPE="${MODEL_TYPE:-all}"

# Rewrite short flags to canonical long forms. Value-taking short flags
# consume the next positional as their value.
args=()
while [ $# -gt 0 ]; do
    case "$1" in
        -d) args+=(--dry-run); shift ;;
        -r) args+=(--resume); shift ;;
        -T) args+=(--no-tensorboard); shift ;;
        -e) args+=(--epochs "$2"); shift 2 ;;
        -m) args+=(--model-type "$2"); shift 2 ;;
        -t) args+=(--tb-logdir "$2"); shift 2 ;;
        *)  args+=("$1"); shift ;;
    esac
done

echo "Training starting — model=$MODEL_TYPE epochs=$EPOCHS"
echo "Log: $LOG"
echo "Tail with: tail -f '$LOG'"
echo "----------------------------------------"

"$VENV_PYTHON" run_full_training_cycle.py \
    --model-type "$MODEL_TYPE" \
    --epochs "$EPOCHS" \
    "${args[@]}" 2>&1 | tee "$LOG"
RC=${PIPESTATUS[0]}

echo "----------------------------------------"
echo "Training finished (exit $RC). Log archived at $LOG"
exit "$RC"
