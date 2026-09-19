## 03-A-baseline (2026-09-18T23:44:22Z)

set=measured k=3 maxlen=600000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 45.81 | 50.17 | 0.277 |
| C2 | 76.68 | 42.66 | 0.325 |
| C3 | 96.11 | 36.04 | 0.362 |
| C4 | 115.76 | 32.43 | 0.412 |
| C5 | 130.22 | 29.64 | 0.431 |
| C6 | 147.64 | 27.87 | 0.45 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 63.74 | 50.0 | 45.31 | 44.46 | 38.0 | 37.38 |
| json | 50.28 | 49.47 | 32.72 | 28.27 | 27.92 | 25.94 |
| narrative | 34.58 | 27.11 | 22.62 | 19.86 | 17.71 | 16.56 |
| prose | 39.72 | 31.33 | 26.93 | 24.08 | 19.57 | 19.31 |
| math | 62.56 | 52.14 | 43.01 | 40.03 | 39.53 | 34.3 |
| reasoning | 53.56 | 42.4 | 40.44 | 30.83 | 28.14 | 26.46 |
| summary | 35.72 | 30.05 | 29.94 | 21.0 | 19.28 | 21.23 |
| format | 61.17 | 58.81 | 47.36 | 50.88 | 47.01 | 41.8 |
| ceiling_count | 69.51 | 59.64 | 57.28 | 53.58 | 50.43 | 48.81 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.999 | 1475.8 |
| 8000 | 11592 | 7.081 | 1637.0 |
| 32000 | 46810 | 28.05 | 1668.8 |
| 64000 | 93335 | 57.022 | 1636.8 |
