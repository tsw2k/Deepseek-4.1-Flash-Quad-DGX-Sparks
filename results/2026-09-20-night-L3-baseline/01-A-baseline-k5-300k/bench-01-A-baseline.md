## 01-A-baseline (2026-09-19T23:07:22Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 48.73 | 54.57 | 0.308 |
| C2 | 76.31 | 43.11 | 0.34 |
| C3 | 101.61 | 39.08 | 0.371 |
| C4 | 120.46 | 34.82 | 0.398 |
| C5 | 137.2 | 32.17 | 0.447 |
| C6 | 153.93 | 29.74 | 0.48 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 75.5 | 60.73 | 61.91 | 47.85 | 44.21 | 44.44 |
| json | 50.15 | 36.17 | 31.18 | 32.32 | 28.38 | 28.64 |
| narrative | 27.95 | 23.17 | 19.93 | 16.43 | 15.49 | 14.54 |
| prose | 35.52 | 26.31 | 21.11 | 20.08 | 18.15 | 16.67 |
| math | 74.28 | 59.37 | 50.45 | 46.18 | 45.98 | 41.78 |
| reasoning | 63.08 | 41.27 | 36.91 | 35.14 | 28.41 | 26.44 |
| summary | 30.64 | 26.49 | 24.05 | 21.59 | 19.17 | 16.69 |
| format | 79.41 | 71.36 | 67.13 | 58.98 | 57.61 | 48.73 |
| ceiling_count | 88.66 | 78.52 | 71.57 | 62.93 | 59.31 | 56.59 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.985 | 1486.0 |
| 8000 | 11592 | 7.218 | 1606.0 |
| 32000 | 46810 | 27.89 | 1678.4 |
| 64000 | 93335 | 56.34 | 1656.6 |
