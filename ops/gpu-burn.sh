#!/usr/bin/env bash
# 15 s fp16 matmul burn with the clock sampled under load. Catches the GB10 clock latch, where
# the embedded controller holds the GPU below 1 GHz with nothing visible in nvidia-smi. In TP4
# every collective waits for the slowest rank, so one latched node sets the pace for all four.
#
#   ops/gpu-burn.sh [image]        exit 1 below 60 TFLOPS
#
# Healthy GB10 (Tech2Wild/Kai, 2026-09-10): 75-90 TFLOPS, ~2200-2400 MHz, 80 W+ under load.
# Latched: ~715 MHz, ~18 W. A reboot does not clear it; unplugging the adapter for 30-60 s does.
# Needs the GPU free: run it before a launch, never next to a serving rank.
set -euo pipefail
image=${1:-vllm-dsv41:172d9a17}
out=$(mktemp)
docker run --rm --gpus all --network none --entrypoint python3 "$image" -c "
import torch, time
a = torch.randn(4096, 4096, dtype=torch.float16, device='cuda')
b = torch.randn(4096, 4096, dtype=torch.float16, device='cuda')
for _ in range(10): c = a @ b
torch.cuda.synchronize(); t0 = time.time(); n = 0
while time.time() - t0 < 15:
    c = a @ b; n += 1
torch.cuda.synchronize()
print(f'{2 * 4096**3 * n / (time.time() - t0) / 1e12:.1f}')
" > "$out" 2>/dev/null &
pid=$!
sleep 12
load=$(nvidia-smi --query-gpu=clocks.sm,power.draw --format=csv,noheader | tr -d '\n')
wait $pid
tflops=$(tail -1 "$out")
rm -f "$out"
echo "$(hostname): ${tflops} TFLOPS, under load: $load"
awk -v t="$tflops" 'BEGIN { exit !(t >= 60) }'
