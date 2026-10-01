## 01-A-baseline (2026-09-30T23:07:14Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 48.45 | 54.74 | 0.312 |
| C2 | 76.36 | 43.7 | 0.333 |
| C3 | 98.02 | 37.95 | 0.389 |
| C4 | 120.81 | 34.58 | 0.43 |
| C5 | 135.15 | 31.43 | 0.446 |
| C6 | 150.91 | 29.55 | 0.473 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 73.83 | 61.07 | 56.66 | 52.63 | 43.54 | 42.0 |
| json | 48.02 | 42.43 | 35.48 | 31.24 | 30.19 | 29.94 |
| narrative | 28.24 | 23.3 | 17.82 | 17.06 | 15.33 | 13.98 |
| prose | 36.77 | 25.27 | 22.61 | 19.76 | 17.49 | 16.69 |
| math | 75.93 | 54.95 | 48.22 | 52.0 | 41.08 | 40.02 |
| reasoning | 50.03 | 45.33 | 36.45 | 32.25 | 28.96 | 27.96 |
| summary | 40.77 | 29.33 | 22.62 | 18.28 | 18.27 | 18.28 |
| format | 84.32 | 67.89 | 63.7 | 53.43 | 56.54 | 47.53 |
| ceiling_count | 90.28 | 79.03 | 71.32 | 62.71 | 60.49 | 56.66 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 2.003 | 1472.5 |
| 8000 | 11592 | 7.226 | 1604.2 |
| 32000 | 46810 | 27.931 | 1675.9 |
| 64000 | 93335 | 56.387 | 1655.3 |
