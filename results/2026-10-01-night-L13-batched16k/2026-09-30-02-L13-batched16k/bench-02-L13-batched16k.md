## 02-L13-batched16k (2026-09-30T23:29:36Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 50.4 | 56.84 | 0.308 |
| C2 | 77.05 | 44.34 | 0.345 |
| C3 | 95.52 | 36.41 | 0.377 |
| C4 | 114.8 | 33.35 | 0.445 |
| C5 | 137.67 | 31.82 | 0.433 |
| C6 | 149.26 | 29.16 | 0.486 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 75.5 | 57.66 | 50.15 | 47.96 | 46.03 | 45.15 |
| json | 61.49 | 49.85 | 34.34 | 29.54 | 28.39 | 27.7 |
| narrative | 32.69 | 21.26 | 18.54 | 17.74 | 16.7 | 14.56 |
| prose | 31.45 | 24.37 | 20.87 | 19.27 | 17.71 | 16.44 |
| math | 82.58 | 58.66 | 50.05 | 44.69 | 44.87 | 38.91 |
| reasoning | 59.23 | 45.21 | 35.05 | 33.21 | 32.84 | 27.73 |
| summary | 34.44 | 24.87 | 22.42 | 19.02 | 19.57 | 15.62 |
| format | 77.35 | 72.86 | 59.9 | 55.35 | 48.49 | 47.16 |
| ceiling_count | 89.27 | 78.6 | 71.2 | 63.5 | 60.54 | 56.18 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.979 | 1490.7 |
| 8000 | 11592 | 7.009 | 1653.9 |
| 32000 | 46810 | 28.197 | 1660.1 |
| 64000 | 93335 | 57.393 | 1626.2 |
