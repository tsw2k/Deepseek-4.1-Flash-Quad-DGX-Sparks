## 03-A-baseline (2026-09-30T23:49:52Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.15 | 54.89 | 0.305 |
| C2 | 75.42 | 43.28 | 0.347 |
| C3 | 96.07 | 37.14 | 0.375 |
| C4 | 122.89 | 35.24 | 0.402 |
| C5 | 134.91 | 31.37 | 0.447 |
| C6 | 158.72 | 30.62 | 0.453 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 76.08 | 64.87 | 53.24 | 48.8 | 46.93 | 44.52 |
| json | 46.42 | 43.46 | 37.77 | 34.63 | 31.11 | 28.04 |
| narrative | 30.54 | 23.99 | 18.38 | 16.8 | 16.44 | 14.71 |
| prose | 36.37 | 26.29 | 23.49 | 20.21 | 17.1 | 17.01 |
| math | 75.79 | 57.17 | 48.29 | 51.76 | 43.14 | 43.48 |
| reasoning | 58.28 | 42.54 | 34.99 | 31.41 | 29.4 | 26.36 |
| summary | 36.97 | 27.34 | 24.61 | 21.36 | 16.51 | 17.83 |
| format | 78.66 | 60.56 | 56.34 | 56.92 | 50.32 | 52.99 |
| ceiling_count | 90.66 | 79.03 | 70.96 | 63.02 | 59.4 | 56.68 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.994 | 1479.1 |
| 8000 | 11592 | 7.286 | 1591.0 |
| 32000 | 46810 | 27.775 | 1685.3 |
| 64000 | 93335 | 56.356 | 1656.2 |
