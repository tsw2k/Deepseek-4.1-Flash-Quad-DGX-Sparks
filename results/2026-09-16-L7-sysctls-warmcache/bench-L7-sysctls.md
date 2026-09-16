## L7-sysctls (2026-09-16T10:00:13Z)

set=measured k=3 maxlen=600000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 45.05 | 49.51 | 0.276 |
| C2 | 73.91 | 40.92 | 0.326 |
| C3 | 90.18 | 33.16 | 0.358 |
| C4 | 109.1 | 30.95 | 0.408 |
| C5 | 127.67 | 29.01 | 0.391 |
| C6 | 142.44 | 26.86 | 0.404 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 59.96 | 49.32 | 44.49 | 39.02 | 41.69 | 36.41 |
| json | 45.19 | 37.83 | 28.58 | 30.47 | 27.6 | 26.35 |
| narrative | 32.42 | 27.51 | 20.21 | 19.75 | 16.69 | 17.14 |
| prose | 36.08 | 33.02 | 25.42 | 23.02 | 22.09 | 18.9 |
| math | 63.64 | 51.03 | 46.17 | 37.27 | 35.38 | 32.25 |
| reasoning | 57.7 | 43.37 | 32.2 | 30.86 | 27.93 | 25.35 |
| summary | 35.12 | 33.5 | 23.63 | 21.78 | 19.94 | 19.03 |
| format | 65.96 | 51.77 | 44.54 | 45.42 | 40.78 | 39.42 |
| ceiling_count | 71.2 | 59.79 | 57.18 | 50.04 | 47.67 | 46.67 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 0.363 | 8122.6 |
| 8000 | 11592 | 0.346 | 33498.5 |
| 32000 | 46810 | 0.443 | 105571.9 |
| 64000 | 93335 | 0.48 | 194485.2 |
