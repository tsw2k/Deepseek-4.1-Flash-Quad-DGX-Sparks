## 01-A-baseline (2026-09-18T23:07:21Z)

set=measured k=3 maxlen=600000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 45.39 | 49.98 | 0.29 |
| C2 | 74.4 | 41.7 | 0.326 |
| C3 | 94.91 | 35.62 | 0.373 |
| C4 | 115.84 | 32.72 | 0.39 |
| C5 | 134.37 | 30.35 | 0.442 |
| C6 | 152.25 | 28.61 | 0.446 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 63.68 | 55.56 | 47.3 | 42.19 | 41.19 | 37.21 |
| json | 44.81 | 37.14 | 29.94 | 34.48 | 29.53 | 26.71 |
| narrative | 32.67 | 25.36 | 24.32 | 19.31 | 17.72 | 16.21 |
| prose | 36.67 | 30.34 | 26.34 | 22.92 | 21.18 | 19.53 |
| math | 62.61 | 50.17 | 42.72 | 44.07 | 38.06 | 36.16 |
| reasoning | 57.02 | 44.31 | 35.43 | 31.68 | 27.51 | 26.08 |
| summary | 37.42 | 30.92 | 24.07 | 22.82 | 19.66 | 19.36 |
| format | 64.95 | 59.8 | 54.84 | 44.31 | 47.92 | 47.59 |
| ceiling_count | 69.91 | 60.0 | 54.54 | 53.86 | 49.95 | 48.69 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 2.004 | 1472.3 |
| 8000 | 11592 | 7.189 | 1612.6 |
| 32000 | 46810 | 28.185 | 1660.8 |
| 64000 | 93335 | 56.812 | 1642.9 |
