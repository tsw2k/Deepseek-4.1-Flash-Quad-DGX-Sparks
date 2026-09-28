## 06-A-baseline (2026-09-28T18:05:36Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.29 | 54.94 | 0.296 |
| C2 | 78.43 | 45.17 | 0.348 |
| C3 | 101.22 | 39.12 | 0.369 |
| C4 | 116.46 | 33.55 | 0.422 |
| C5 | 141.75 | 32.73 | 0.42 |
| C6 | 152.34 | 29.37 | 0.485 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 76.28 | 59.51 | 56.29 | 51.31 | 46.65 | 42.51 |
| json | 46.32 | 46.93 | 36.41 | 30.01 | 25.6 | 28.8 |
| narrative | 34.41 | 24.86 | 19.52 | 16.73 | 15.44 | 15.02 |
| prose | 33.49 | 24.51 | 21.22 | 20.21 | 18.06 | 17.05 |
| math | 74.88 | 61.52 | 52.68 | 44.35 | 50.16 | 37.96 |
| reasoning | 61.63 | 43.8 | 37.75 | 31.89 | 30.19 | 28.82 |
| summary | 31.82 | 27.2 | 25.22 | 20.64 | 20.02 | 16.31 |
| format | 80.69 | 73.01 | 63.91 | 53.24 | 55.76 | 48.47 |
| ceiling_count | 90.04 | 79.65 | 72.12 | 63.45 | 60.66 | 56.37 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.984 | 1486.6 |
| 8000 | 11592 | 7.305 | 1586.9 |
| 32000 | 46810 | 27.75 | 1686.9 |
| 64000 | 93335 | 56.328 | 1657.0 |
