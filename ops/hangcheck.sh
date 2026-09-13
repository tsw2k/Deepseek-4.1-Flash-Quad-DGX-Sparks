#!/usr/bin/env bash
# Print HANG when the last 90 s of vLLM stats show running requests and zero generation.
# That is the signature of a padded speculative batch stuck in SM120 sparse MLA (FlashInfer
# #5015) or a stalled collective: the process stays up, the GPU looks busy, nothing moves.
# From Tech2Wild/Kai's hangcheck.sh.
#
#   ops/hangcheck.sh [container]        exit 1 on HANG
name=${1:-vllm_dsv41}
lines=$(docker logs --since 3m "$name" 2>&1 | grep "Avg generation throughput" | tail -9)
n=$(printf '%s\n' "$lines" | grep -c .)
z=$(printf '%s\n' "$lines" | grep -cE "Avg generation throughput: 0\.0 tokens/s, Running: [1-9]")
last=$(printf '%s\n' "$lines" | tail -1 | grep -oE "generation throughput: [0-9.]+ tokens/s, Running: [0-9]+ reqs")
if [ "$n" -ge 9 ] && [ "$z" -eq "$n" ]; then
  echo "HANG: 90 s of 0.0 tok/s with requests running"
  exit 1
fi
echo "ok (${last:-no stats yet})"
