#!/bin/bash
# Macena CS2 Analyzer — full-cycle AI training.
#
# Runs run_full_training_cycle.py.
#
# --model-type is REQUIRED. Choices:
#   jepa_v2   — JEPA v2 pre-training (wave-2 module; exits 1 if not yet available)
#   coach_v2  — Coach v2 (not yet implemented; raises NotImplementedError)
#   all       — jepa_v2 then coach_v2 (currently fails until coach_v2 lands in step 6)
#   jepa      — Legacy JEPA (requires ALLOW_LEGACY_NEURAL_TRAINING=True)
#   rap       — Legacy RAP  (requires ALLOW_LEGACY_NEURAL_TRAINING=True + USE_RAP_MODEL=True)
#
# Checkpoints land in Programma_CS2_RENAN/models/.
# TensorBoard events land in Programma_CS2_RENAN/runs/ (see RUNS_DIR in config).
#
# Env overrides:
#   EPOCHS=30 ./train.sh --model-type jepa      # cap at 30 epochs (legacy types only)
#   MODEL_TYPE=jepa_v2 ./train.sh               # via env (fallback to 'all' if unset)
#
# jepa_v2 budgets in STEPS, not epochs (D-36): --epochs/EPOCHS are ignored for it.
#   ./train.sh --model-type jepa_v2 --steps 20000 --probe-every 500
#   ./train.sh --model-type jepa_v2 --data-dir "$DATA/cs2_v2" --no-resume
#
# Usage:
#   ./train.sh --model-type jepa_v2              # v2 pre-training
#   ./train.sh -d --model-type jepa_v2           # 60-step smoke test, writes NO checkpoint (D-35)
#   ./train.sh -e 30 --model-type jepa           # cap epochs (legacy types; overrides env)
#   ./train.sh -m jepa --model-type jepa         # legacy JEPA (gated)
#   ./train.sh -t PATH --model-type jepa_v2      # TensorBoard log directory
#   ./train.sh -T --model-type jepa_v2           # disable TensorBoard
#
# Short flags are rewritten to the canonical long form before forwarding to
# run_full_training_cycle.py (whose argparse only declares long options).
set -e
cd "$(dirname "$0")"

# Repo-local venv is the project's canonical interpreter (lock files and
# docs/QUICKSTART.md target .venv); ~/.venvs/cs2analyzer is kept only as a
# fallback for legacy setups.
VENV_PYTHON="$(dirname "$0")/.venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
    VENV_PYTHON="$HOME/.venvs/cs2analyzer/bin/python"
fi
if [ ! -x "$VENV_PYTHON" ]; then
    echo "ERROR: no venv found at ./.venv or ~/.venvs/cs2analyzer" >&2
    echo "Create it with: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-rap.txt" >&2
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
