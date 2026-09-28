## 01-A-baseline (2026-09-28T16:41:56Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.91 | 56.08 | 0.307 |
| C2 | 75.55 | 42.72 | 0.35 |
| C3 | 95.31 | 36.28 | 0.386 |
| C4 | 120.19 | 34.81 | 0.412 |
| C5 | 133.2 | 31.54 | 0.445 |
| C6 | 152.5 | 29.18 | 0.447 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 81.01 | 57.85 | 51.98 | 48.58 | 45.56 | 43.38 |
| json | 47.4 | 37.24 | 31.98 | 37.64 | 29.47 | 26.01 |
| narrative | 33.09 | 22.75 | 18.46 | 19.16 | 16.25 | 14.28 |
| prose | 33.51 | 24.98 | 21.59 | 20.15 | 17.41 | 16.73 |
| math | 78.07 | 55.65 | 53.53 | 47.68 | 41.98 | 37.69 |
| reasoning | 61.21 | 45.46 | 37.25 | 31.51 | 28.87 | 27.49 |
| summary | 34.25 | 28.35 | 20.7 | 18.95 | 19.61 | 17.64 |
| format | 80.09 | 69.48 | 54.73 | 54.79 | 53.19 | 50.23 |
| ceiling_count | 90.42 | 79.08 | 67.6 | 63.32 | 59.93 | 56.61 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.915 | 1540.3 |
| 8000 | 11592 | 7.067 | 1640.4 |
| 32000 | 46810 | 27.694 | 1690.2 |
| 64000 | 93335 | 56.119 | 1663.2 |
