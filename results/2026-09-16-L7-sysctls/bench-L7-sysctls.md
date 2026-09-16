## L7-sysctls (2026-09-16T10:14:45Z)

set=measured k=3 maxlen=600000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 45.89 | 50.41 | 0.283 |
| C2 | 71.18 | 39.83 | 0.327 |
| C3 | 96.77 | 36.37 | 0.363 |
| C4 | 87.96 | 26.65 | 7.918 |
| C5 | 97.64 | 22.02 | 0.516 |
| C6 | 117.74 | 22.21 | 0.575 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 65.0 | 49.03 | 43.99 | 40.56 | 30.09 | 27.57 |
| json | 53.22 | 35.23 | 35.05 | 27.81 | 21.86 | 19.14 |
| narrative | 34.34 | 24.91 | 22.52 | 15.66 | 14.2 | 12.66 |
| prose | 39.52 | 30.24 | 26.33 | 18.28 | 16.91 | 16.54 |
| math | 63.67 | 49.53 | 47.65 | 30.75 | 26.29 | 28.98 |
| reasoning | 51.4 | 41.47 | 36.12 | 24.36 | 20.63 | 23.28 |
| summary | 33.46 | 28.49 | 25.16 | 18.73 | 17.05 | 16.62 |
| format | 62.65 | 59.7 | 54.1 | 37.06 | 29.09 | 32.93 |
| ceiling_count | 69.31 | 59.11 | 57.49 | 37.45 | 33.47 | 35.64 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 2.026 | 1456.1 |
| 8000 | 11592 | 7.134 | 1624.9 |
| 32000 | 46810 | 28.138 | 1663.6 |
| 64000 | 93335 | 57.513 | 1622.9 |
