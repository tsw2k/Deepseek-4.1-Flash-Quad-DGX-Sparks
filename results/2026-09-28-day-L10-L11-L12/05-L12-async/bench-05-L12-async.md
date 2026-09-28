## 05-L12-async (2026-09-28T17:48:52Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 48.87 | 54.67 | 0.303 |
| C2 | 78.24 | 44.78 | 0.34 |
| C3 | 101.29 | 39.89 | 0.381 |
| C4 | 119.27 | 34.65 | 0.419 |
| C5 | 136.36 | 31.61 | 0.421 |
| C6 | 157.24 | 30.87 | 0.456 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 76.65 | 63.14 | 53.73 | 48.07 | 46.65 | 45.36 |
| json | 50.53 | 47.99 | 47.08 | 35.76 | 29.78 | 28.2 |
| narrative | 30.92 | 22.35 | 18.83 | 17.64 | 16.09 | 14.54 |
| prose | 35.07 | 24.66 | 22.09 | 19.3 | 18.07 | 17.13 |
| math | 74.93 | 59.45 | 52.79 | 45.66 | 41.98 | 42.74 |
| reasoning | 58.4 | 43.5 | 38.6 | 33.62 | 30.46 | 26.84 |
| summary | 30.81 | 28.09 | 21.72 | 20.71 | 19.35 | 18.52 |
| format | 80.08 | 69.07 | 64.26 | 56.43 | 50.46 | 53.66 |
| ceiling_count | 88.87 | 79.95 | 71.8 | 62.86 | 65.29 | 55.89 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.98 | 1489.7 |
| 8000 | 11592 | 7.211 | 1607.4 |
| 32000 | 46810 | 27.842 | 1681.3 |
| 64000 | 93335 | 56.33 | 1656.9 |
