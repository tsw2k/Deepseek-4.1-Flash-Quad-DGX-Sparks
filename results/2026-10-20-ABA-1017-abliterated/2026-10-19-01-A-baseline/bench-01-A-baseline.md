## 01-A-baseline (2026-10-19T23:07:06Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 NCCL_IB_HCA=rocep1s0f1,roceP2p1s0f1 NCCL_IB_ADDR_RANGE=10.77.0.0/16 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 50.18 | 55.91 | 0.301 |
| C2 | 75.25 | 43.47 | 0.339 |
| C3 | 103.83 | 39.87 | 0.381 |
| C4 | 124.4 | 36.38 | 0.391 |
| C5 | 148.03 | 34.19 | 0.417 |
| C6 | 162.44 | 31.83 | 0.482 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 80.39 | 64.39 | 64.09 | 56.3 | 49.75 | 51.65 |
| json | 63.99 | 47.72 | 37.62 | 36.11 | 36.75 | 34.47 |
| narrative | 29.85 | 25.17 | 20.16 | 18.41 | 14.98 | 14.93 |
| prose | 35.59 | 26.48 | 26.09 | 22.67 | 22.32 | 19.38 |
| math | 67.88 | 55.46 | 49.42 | 44.53 | 42.7 | 39.58 |
| reasoning | 57.88 | 41.38 | 37.32 | 33.98 | 31.46 | 30.88 |
| summary | 38.26 | 29.82 | 23.08 | 22.25 | 20.15 | 18.77 |
| format | 73.41 | 57.33 | 61.17 | 56.81 | 55.38 | 45.0 |
| ceiling_count | 90.73 | 79.83 | 73.47 | 69.62 | 65.43 | 62.08 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.896 | 1555.9 |
| 8000 | 11592 | 6.698 | 1730.6 |
| 32000 | 46810 | 25.329 | 1848.1 |
| 64000 | 93335 | 51.22 | 1822.2 |
