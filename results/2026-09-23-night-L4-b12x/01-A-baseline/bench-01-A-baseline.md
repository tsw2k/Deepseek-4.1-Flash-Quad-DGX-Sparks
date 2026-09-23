## 01-A-baseline (2026-09-22T23:07:52Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.02 | 55.47 | 0.311 |
| C2 | 74.45 | 42.86 | 0.346 |
| C3 | 95.25 | 36.92 | 0.384 |
| C4 | 119.27 | 34.51 | 0.403 |
| C5 | 135.9 | 31.69 | 0.456 |
| C6 | 151.85 | 29.67 | 0.481 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 74.65 | 57.85 | 56.92 | 48.39 | 44.04 | 43.61 |
| json | 56.2 | 50.95 | 34.4 | 33.24 | 29.01 | 29.1 |
| narrative | 28.61 | 22.39 | 18.13 | 17.74 | 16.36 | 14.81 |
| prose | 33.47 | 25.71 | 22.43 | 20.12 | 17.78 | 17.0 |
| math | 76.74 | 54.19 | 48.03 | 48.87 | 43.36 | 38.48 |
| reasoning | 55.52 | 44.85 | 34.92 | 31.76 | 28.67 | 28.16 |
| summary | 38.38 | 25.97 | 20.73 | 22.62 | 16.58 | 17.23 |
| format | 80.17 | 60.93 | 59.83 | 53.32 | 57.7 | 48.95 |
| ceiling_count | 89.43 | 77.51 | 70.48 | 62.15 | 59.34 | 55.94 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.951 | 1512.2 |
| 8000 | 11592 | 6.946 | 1668.9 |
| 32000 | 46810 | 27.71 | 1689.3 |
| 64000 | 93335 | 56.504 | 1651.8 |
