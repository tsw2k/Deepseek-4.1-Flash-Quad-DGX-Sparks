## 03-A-baseline (2026-09-28T17:14:22Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 50.38 | 56.54 | 0.302 |
| C2 | 75.72 | 42.83 | 0.336 |
| C3 | 102.11 | 39.45 | 0.389 |
| C4 | 115.66 | 33.38 | 0.398 |
| C5 | 135.54 | 31.51 | 0.443 |
| C6 | 151.15 | 29.27 | 0.471 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 80.34 | 57.21 | 50.39 | 46.51 | 46.67 | 40.58 |
| json | 54.67 | 43.43 | 37.83 | 30.63 | 30.73 | 29.28 |
| narrative | 29.55 | 19.92 | 19.19 | 16.41 | 15.44 | 14.53 |
| prose | 34.22 | 24.52 | 21.91 | 19.77 | 17.17 | 16.13 |
| math | 74.67 | 58.8 | 64.31 | 46.43 | 42.56 | 40.83 |
| reasoning | 62.84 | 44.59 | 36.06 | 31.9 | 29.9 | 28.06 |
| summary | 35.12 | 32.18 | 21.93 | 22.38 | 18.87 | 17.63 |
| format | 80.92 | 61.95 | 63.96 | 53.01 | 50.74 | 47.09 |
| ceiling_count | 90.73 | 79.19 | 72.03 | 62.81 | 60.77 | 56.74 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.983 | 1487.5 |
| 8000 | 11592 | 7.074 | 1638.6 |
| 32000 | 46810 | 28.006 | 1671.4 |
| 64000 | 93335 | 56.113 | 1663.3 |
