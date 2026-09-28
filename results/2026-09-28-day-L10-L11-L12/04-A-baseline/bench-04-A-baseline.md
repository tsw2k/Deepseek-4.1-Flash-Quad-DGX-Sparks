## 04-A-baseline (2026-09-28T17:31:37Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.26 | 55.27 | 0.305 |
| C2 | 81.09 | 46.3 | 0.334 |
| C3 | 95.78 | 36.59 | 0.384 |
| C4 | 125.92 | 35.97 | 0.396 |
| C5 | 141.91 | 32.93 | 0.432 |
| C6 | 152.26 | 29.46 | 0.443 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 76.17 | 60.36 | 50.68 | 47.1 | 49.14 | 42.72 |
| json | 48.81 | 52.18 | 32.57 | 33.73 | 28.25 | 26.77 |
| narrative | 29.26 | 22.69 | 19.33 | 16.79 | 16.21 | 14.78 |
| prose | 36.77 | 25.2 | 20.51 | 21.76 | 17.9 | 15.9 |
| math | 75.57 | 69.12 | 48.2 | 52.94 | 42.61 | 38.37 |
| reasoning | 60.13 | 43.38 | 38.83 | 31.94 | 30.16 | 26.63 |
| summary | 35.43 | 25.01 | 23.37 | 22.43 | 19.67 | 17.65 |
| format | 79.99 | 72.44 | 59.26 | 61.09 | 59.49 | 52.85 |
| ceiling_count | 90.16 | 78.58 | 70.92 | 62.95 | 60.58 | 56.38 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.931 | 1527.9 |
| 8000 | 11592 | 7.152 | 1620.8 |
| 32000 | 46810 | 27.997 | 1672.0 |
| 64000 | 93335 | 56.356 | 1656.2 |
