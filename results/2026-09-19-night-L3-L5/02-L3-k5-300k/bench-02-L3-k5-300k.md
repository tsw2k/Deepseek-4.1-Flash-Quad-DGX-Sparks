## 02-L3-k5-300k (2026-09-18T23:26:24Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.14 | 55.52 | 0.315 |
| C2 | 77.1 | 43.84 | 0.339 |
| C3 | 99.13 | 37.6 | 0.37 |
| C4 | 118.25 | 34.2 | 0.401 |
| C5 | 142.33 | 32.66 | 0.432 |
| C6 | 156.48 | 30.1 | 0.458 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 77.33 | 59.98 | 53.56 | 46.4 | 43.98 | 41.73 |
| json | 53.4 | 42.0 | 37.01 | 32.93 | 29.3 | 26.92 |
| narrative | 29.08 | 21.77 | 17.92 | 16.96 | 16.12 | 13.89 |
| prose | 34.47 | 23.13 | 22.81 | 20.78 | 17.27 | 16.57 |
| math | 77.84 | 60.13 | 56.32 | 45.94 | 47.56 | 40.2 |
| reasoning | 57.34 | 43.74 | 34.24 | 31.02 | 29.71 | 27.08 |
| summary | 31.42 | 27.82 | 23.31 | 20.96 | 18.5 | 20.22 |
| format | 83.32 | 72.11 | 55.6 | 58.6 | 58.87 | 54.18 |
| ceiling_count | 88.88 | 77.42 | 70.75 | 62.55 | 59.92 | 55.82 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.952 | 1511.4 |
| 8000 | 11592 | 7.107 | 1631.0 |
| 32000 | 46810 | 28.29 | 1654.7 |
| 64000 | 93335 | 56.617 | 1648.5 |
