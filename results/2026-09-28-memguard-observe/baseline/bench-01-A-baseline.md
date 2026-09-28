## 01-A-baseline (2026-09-28T14:06:35Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 48.52 | 54.53 | 0.307 |
| C2 | 81.23 | 46.8 | 0.332 |
| C3 | 101.02 | 38.8 | 0.371 |
| C4 | 125.0 | 35.72 | 0.393 |
| C5 | 141.45 | 33.21 | 0.437 |
| C6 | 158.95 | 30.82 | 0.444 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 79.04 | 58.53 | 51.4 | 50.83 | 55.62 | 43.32 |
| json | 51.41 | 57.67 | 33.35 | 30.69 | 30.44 | 29.82 |
| narrative | 26.67 | 22.39 | 20.47 | 17.2 | 15.81 | 14.79 |
| prose | 33.99 | 24.17 | 24.21 | 20.94 | 18.21 | 16.77 |
| math | 75.61 | 57.47 | 50.25 | 47.17 | 43.97 | 41.13 |
| reasoning | 57.18 | 51.44 | 37.84 | 35.13 | 31.66 | 28.18 |
| summary | 31.16 | 28.81 | 24.11 | 23.19 | 19.13 | 18.54 |
| format | 81.15 | 73.88 | 68.74 | 60.58 | 50.87 | 53.99 |
| ceiling_count | 92.44 | 79.39 | 72.4 | 64.05 | 61.52 | 56.43 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.953 | 1510.6 |
| 8000 | 11592 | 7.073 | 1638.8 |
| 32000 | 46810 | 28.048 | 1668.9 |
| 64000 | 93335 | 56.306 | 1657.6 |
