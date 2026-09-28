## 02-L10-engram64 (2026-09-28T16:58:11Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 DSV41_ENGRAM_DISK_THREADS=64 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.91 | 55.96 | 0.297 |
| C2 | 77.78 | 44.27 | 0.343 |
| C3 | 96.57 | 37.49 | 0.382 |
| C4 | 121.93 | 35.12 | 0.417 |
| C5 | 134.9 | 31.65 | 0.445 |
| C6 | 150.84 | 29.43 | 0.478 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 79.2 | 64.57 | 57.18 | 50.35 | 44.97 | 41.99 |
| json | 57.28 | 41.23 | 37.61 | 32.82 | 29.3 | 28.11 |
| narrative | 30.56 | 21.51 | 19.28 | 17.66 | 15.43 | 14.13 |
| prose | 35.12 | 25.01 | 20.82 | 19.22 | 19.95 | 17.29 |
| math | 75.05 | 56.25 | 48.39 | 47.38 | 42.84 | 39.91 |
| reasoning | 59.34 | 48.97 | 37.14 | 32.22 | 29.64 | 27.9 |
| summary | 33.25 | 24.68 | 21.47 | 18.94 | 20.25 | 17.12 |
| format | 77.88 | 71.92 | 58.03 | 62.39 | 50.79 | 48.95 |
| ceiling_count | 86.34 | 78.21 | 72.12 | 62.99 | 59.34 | 57.36 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.828 | 1613.8 |
| 8000 | 11592 | 7.065 | 1640.8 |
| 32000 | 46810 | 27.014 | 1732.8 |
| 64000 | 93335 | 54.953 | 1698.5 |
