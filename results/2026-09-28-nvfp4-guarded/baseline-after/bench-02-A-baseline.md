## 02-A-baseline (2026-09-28T15:29:48Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 50.79 | 56.99 | 0.302 |
| C2 | 77.85 | 44.98 | 0.331 |
| C3 | 94.57 | 36.53 | 0.368 |
| C4 | 118.2 | 34.2 | 0.403 |
| C5 | 136.34 | 31.85 | 0.44 |
| C6 | 154.57 | 29.61 | 0.449 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 78.61 | 60.11 | 51.21 | 52.81 | 47.85 | 43.23 |
| json | 47.1 | 47.59 | 36.6 | 32.03 | 31.95 | 27.68 |
| narrative | 33.53 | 25.77 | 19.56 | 17.0 | 15.43 | 14.82 |
| prose | 34.7 | 25.6 | 21.71 | 19.65 | 18.09 | 16.65 |
| math | 77.75 | 60.32 | 49.1 | 48.21 | 42.36 | 40.61 |
| reasoning | 64.96 | 42.1 | 35.69 | 32.04 | 29.65 | 28.78 |
| summary | 37.69 | 27.63 | 24.36 | 19.93 | 16.96 | 17.55 |
| format | 81.59 | 70.69 | 54.04 | 51.94 | 52.49 | 47.59 |
| ceiling_count | 92.46 | 80.06 | 72.13 | 63.53 | 65.47 | 56.86 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.969 | 1498.3 |
| 8000 | 11592 | 7.343 | 1578.6 |
| 32000 | 46810 | 28.28 | 1655.2 |
| 64000 | 93335 | 56.771 | 1644.1 |
