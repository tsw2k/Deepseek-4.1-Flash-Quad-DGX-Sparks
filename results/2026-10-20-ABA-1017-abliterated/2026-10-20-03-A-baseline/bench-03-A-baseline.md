## 03-A-baseline (2026-10-20T00:17:37Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 NCCL_IB_HCA=rocep1s0f1,roceP2p1s0f1 NCCL_IB_ADDR_RANGE=10.77.0.0/16 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.46 | 55.15 | 0.302 |
| C2 | 81.19 | 46.7 | 0.33 |
| C3 | 96.99 | 37.89 | 0.393 |
| C4 | 125.98 | 36.94 | 0.412 |
| C5 | 143.62 | 33.61 | 0.44 |
| C6 | 165.93 | 32.55 | 0.485 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 80.85 | 70.45 | 57.55 | 57.01 | 52.25 | 51.31 |
| json | 60.03 | 50.72 | 39.71 | 36.45 | 36.05 | 34.15 |
| narrative | 33.27 | 23.36 | 20.11 | 18.0 | 15.5 | 14.94 |
| prose | 34.01 | 28.3 | 24.87 | 21.96 | 21.32 | 19.07 |
| math | 69.54 | 53.86 | 43.87 | 47.36 | 41.62 | 36.84 |
| reasoning | 54.0 | 45.26 | 35.29 | 35.77 | 29.95 | 32.05 |
| summary | 38.94 | 28.83 | 23.99 | 21.58 | 18.18 | 17.43 |
| format | 70.55 | 72.84 | 57.7 | 57.39 | 54.0 | 54.63 |
| ceiling_count | 90.8 | 80.66 | 72.9 | 69.43 | 65.74 | 62.29 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.854 | 1591.2 |
| 8000 | 11592 | 6.416 | 1806.8 |
| 32000 | 46810 | 25.551 | 1832.0 |
| 64000 | 93335 | 51.021 | 1829.3 |
