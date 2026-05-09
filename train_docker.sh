#!/bin/bash
# Macena CS2 Analyzer — GPU Training via Docker ROCm
# Usage: ./train_docker.sh [--dry-run] [--resume] [--epochs N] [--model-type jepa|rap|all]
#
# Runs the full training cycle inside the ROCm PyTorch container with
# the RX 9070 XT (gfx1201) discrete GPU. All project deps are installed from
# .cs2_req_no_torch.txt (torch comes from the container image).
# hflayers (Hopfield) is copied from local venv since it's not on PyPI.
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
DATA_ROOT="$(dirname "$PROJECT_ROOT")"
HFLAYERS_SRC="$PROJECT_ROOT/.venv/lib/python3.12/site-packages/hflayers"

ROCM_IMAGE="rocm/pytorch:latest"

echo "=== Macena CS2 Analyzer — Docker GPU Training ==="
echo "Project:  $PROJECT_ROOT"
echo "Data:     $DATA_ROOT"
echo "Image:    $ROCM_IMAGE"
echo "GPU:      RX 9070 XT (gfx1201, native ROCm 7.2 support)"
echo "Args:     $*"
echo "================================================="

exec docker run --rm -it \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add video \
  --shm-size=8g \
  -v "$DATA_ROOT":/workspace \
  -v "$HFLAYERS_SRC":/opt/venv/lib/python3.12/site-packages/hflayers:ro \
  -w /workspace/Counter-Strike-coach-AI-main \
  -e PYTHONPATH=/workspace/Counter-Strike-coach-AI-main \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring \
  "$ROCM_IMAGE" \
  bash -c "
    echo '>>> Installing project dependencies...'
    pip install --quiet -r .cs2_req_no_torch.txt 2>&1 | tail -1
    pip install --quiet 'ncps>=0.0.7,<2.0' 2>&1 | tail -1
    echo '>>> Verifying GPU...'
    python3 -c \"
import torch
dev = torch.device('cuda:0')
print(f'  GPU: {torch.cuda.get_device_name(0)}')
print(f'  VRAM: {torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB')
print(f'  PyTorch: {torch.__version__}')
\"
    echo '>>> Starting training...'
    python3 run_full_training_cycle.py \$@
  " -- "$@"
