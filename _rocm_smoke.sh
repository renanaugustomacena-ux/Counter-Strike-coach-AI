#!/usr/bin/env bash
# ROCm + PyTorch GPU smoke test inside the rocm/pytorch container.
# Run with:  docker run --rm --device=/dev/kfd --device=/dev/dri \
#              --group-add video --group-add render --ipc=host \
#              --security-opt seccomp=unconfined \
#              -v "$PWD":/work -w /work \
#              rocm/pytorch:latest \
#              bash /work/_rocm_smoke.sh
set -euo pipefail
echo "=== rocminfo agents ==="
rocminfo 2>/dev/null | grep -E "Marketing Name|Name:|gfx" | head -10 || echo "(rocminfo not available in image)"
echo ""
echo "=== rocm-smi GPU live state ==="
rocm-smi 2>&1 | head -20 || echo "(rocm-smi not available)"
echo ""
echo "=== PyTorch flavour ==="
python - <<'PY'
import torch
print(f"torch:        {torch.__version__}")
print(f"build cuda:   {torch.version.cuda}")
print(f"build hip:    {torch.version.hip}")
print(f"cuda avail:   {torch.cuda.is_available()}")
print(f"device count: {torch.cuda.device_count()}")
for i in range(torch.cuda.device_count()):
    p = torch.cuda.get_device_properties(i)
    print(f"  device {i}: {torch.cuda.get_device_name(i)}")
    print(f"           gfx={getattr(p, 'gcnArchName', '?')}  total_mem={p.total_memory/1024**3:.1f} GiB  multi_processor_count={p.multi_processor_count}")
print()
if not torch.cuda.is_available():
    raise SystemExit("[FAIL] PyTorch did not see the GPU. Check ROCm version / gfx target match for Navi 48 (gfx1201).")
print("=== minimal compute test ===")
a = torch.randn(2048, 2048, device="cuda")
b = torch.randn(2048, 2048, device="cuda")
c = a @ b
torch.cuda.synchronize()
print(f"matmul OK; sum={c.sum().item():.3e}")
PY
