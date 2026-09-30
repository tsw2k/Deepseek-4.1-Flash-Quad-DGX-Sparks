## 03-A-baseline (2026-09-29T23:47:31Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.3 | 55.09 | 0.296 |
| C2 | 73.45 | 41.37 | 0.348 |
| C3 | 97.18 | 37.79 | 0.386 |
| C4 | 118.61 | 34.39 | 0.419 |
| C5 | 136.39 | 31.56 | 0.429 |
| C6 | 151.57 | 29.41 | 0.485 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 76.21 | 56.3 | 53.6 | 48.11 | 44.95 | 42.19 |
| json | 49.52 | 39.27 | 33.11 | 34.84 | 29.76 | 28.09 |
| narrative | 30.88 | 22.94 | 18.84 | 17.48 | 16.05 | 15.5 |
| prose | 38.05 | 24.3 | 21.47 | 19.63 | 18.39 | 17.11 |
| math | 79.14 | 60.65 | 48.77 | 44.94 | 41.94 | 40.42 |
| reasoning | 56.57 | 42.17 | 37.35 | 31.56 | 29.04 | 28.13 |
| summary | 32.28 | 24.26 | 23.66 | 19.64 | 18.97 | 15.84 |
| format | 78.07 | 61.08 | 65.49 | 58.94 | 53.38 | 47.99 |
| ceiling_count | 89.99 | 78.58 | 71.1 | 62.88 | 65.0 | 56.58 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.964 | 1502.0 |
| 8000 | 11592 | 7.185 | 1613.4 |
| 32000 | 46810 | 27.794 | 1684.2 |
| 64000 | 93335 | 56.361 | 1656.0 |
