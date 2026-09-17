## L7-cold-baseline (2026-09-17T18:08:25Z)

set=measured k=3 maxlen=600000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 45.2 | 49.6 | 0.288 |
| C2 | 72.73 | 40.95 | 0.343 |
| C3 | 94.61 | 35.51 | 0.364 |
| C4 | 111.91 | 31.29 | 0.41 |
| C5 | 104.52 | 27.72 | 12.416 |
| C6 | 117.43 | 21.95 | 0.505 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 64.79 | 59.88 | 46.29 | 43.95 | 38.26 | 29.1 |
| json | 52.85 | 39.17 | 33.42 | 31.09 | 27.85 | 21.01 |
| narrative | 35.77 | 24.08 | 21.96 | 18.81 | 17.58 | 14.63 |
| prose | 37.86 | 28.47 | 27.12 | 22.29 | 20.4 | 15.29 |
| math | 61.37 | 49.09 | 41.9 | 38.53 | 35.2 | 28.4 |
| reasoning | 53.24 | 42.91 | 33.62 | 30.44 | 26.62 | 21.96 |
| summary | 37.26 | 25.14 | 24.59 | 20.94 | 19.0 | 15.97 |
| format | 53.65 | 58.83 | 55.21 | 44.26 | 36.87 | 29.26 |
| ceiling_count | 69.34 | 59.49 | 56.99 | 49.95 | 45.28 | 36.09 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.995 | 1478.9 |
| 8000 | 11592 | 7.313 | 1585.0 |
| 32000 | 46810 | 28.187 | 1660.7 |
| 64000 | 93335 | 57.335 | 1627.9 |
