## 05-A-baseline (2026-09-19T00:22:03Z)

set=measured k=3 maxlen=600000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 45.93 | 50.48 | 0.292 |
| C2 | 73.55 | 40.66 | 0.33 |
| C3 | 94.11 | 35.4 | 0.364 |
| C4 | 116.6 | 32.98 | 0.394 |
| C5 | 130.24 | 29.73 | 0.44 |
| C6 | 147.25 | 27.88 | 0.485 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 64.34 | 59.42 | 44.71 | 41.85 | 40.72 | 36.73 |
| json | 44.47 | 35.3 | 32.86 | 30.93 | 28.09 | 26.86 |
| narrative | 34.89 | 26.89 | 22.64 | 19.4 | 18.47 | 16.67 |
| prose | 41.12 | 30.56 | 25.54 | 23.8 | 19.76 | 19.63 |
| math | 62.5 | 50.06 | 46.97 | 41.94 | 35.97 | 35.48 |
| reasoning | 57.1 | 42.53 | 36.38 | 31.91 | 27.71 | 27.34 |
| summary | 36.73 | 29.3 | 26.18 | 21.83 | 21.21 | 18.1 |
| format | 62.71 | 51.25 | 47.92 | 52.2 | 45.91 | 42.22 |
| ceiling_count | 69.93 | 59.82 | 57.56 | 50.75 | 47.59 | 48.84 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.997 | 1476.9 |
| 8000 | 11592 | 7.032 | 1648.5 |
| 32000 | 46810 | 28.051 | 1668.7 |
| 64000 | 93335 | 56.961 | 1638.6 |
