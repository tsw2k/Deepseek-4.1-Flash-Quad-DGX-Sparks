## 01-A-baseline (2026-09-29T23:07:14Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.27 | 55.2 | 0.305 |
| C2 | 75.23 | 43.0 | 0.341 |
| C3 | 97.61 | 37.41 | 0.37 |
| C4 | 117.05 | 33.91 | 0.418 |
| C5 | 135.07 | 31.61 | 0.449 |
| C6 | 149.51 | 29.23 | 0.454 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 76.21 | 57.3 | 53.48 | 48.61 | 44.14 | 41.8 |
| json | 47.29 | 40.7 | 32.34 | 31.68 | 28.37 | 29.66 |
| narrative | 29.48 | 22.3 | 18.83 | 17.1 | 15.96 | 13.81 |
| prose | 38.58 | 24.61 | 22.64 | 20.63 | 18.63 | 16.11 |
| math | 81.11 | 55.91 | 55.91 | 46.8 | 40.38 | 40.0 |
| reasoning | 58.99 | 44.19 | 33.8 | 33.49 | 30.86 | 26.14 |
| summary | 30.48 | 26.88 | 26.29 | 20.55 | 16.48 | 17.73 |
| format | 79.45 | 72.08 | 55.95 | 52.46 | 58.05 | 48.58 |
| ceiling_count | 90.42 | 78.37 | 67.86 | 62.84 | 58.73 | 56.23 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.973 | 1494.8 |
| 8000 | 11592 | 7.227 | 1604.1 |
| 32000 | 46810 | 27.756 | 1686.5 |
| 64000 | 93335 | 56.439 | 1653.7 |
