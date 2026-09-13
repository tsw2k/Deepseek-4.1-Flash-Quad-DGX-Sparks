## lever-L1-nccl-buffers (2026-09-13T20:58:32Z)

set=measured k=3 maxlen=600000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 46.13 | 50.71 | 0.282 |
| C2 | 73.13 | 40.65 | 0.338 |
| C3 | 95.81 | 35.91 | 0.37 |
| C4 | 112.8 | 31.62 | 0.389 |
| C5 | 132.55 | 29.95 | 0.44 |
| C6 | 150.95 | 28.51 | 0.443 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 66.8 | 51.42 | 48.03 | 43.87 | 38.22 | 38.67 |
| json | 48.52 | 37.11 | 33.93 | 30.02 | 28.92 | 25.97 |
| narrative | 33.02 | 27.29 | 21.72 | 17.91 | 17.62 | 17.58 |
| prose | 41.02 | 28.97 | 27.21 | 23.36 | 21.06 | 20.04 |
| math | 62.63 | 49.6 | 43.14 | 40.27 | 35.53 | 37.72 |
| reasoning | 54.84 | 41.25 | 32.73 | 30.27 | 30.81 | 26.75 |
| summary | 37.05 | 30.47 | 25.01 | 22.2 | 19.65 | 19.39 |
| format | 61.83 | 59.11 | 55.53 | 45.05 | 47.77 | 41.95 |
| ceiling_count | 69.02 | 63.74 | 57.97 | 53.7 | 49.98 | 48.42 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 2.048 | 1440.6 |
| 8000 | 11592 | 7.148 | 1621.7 |
| 32000 | 46810 | 28.118 | 1664.7 |
| 64000 | 93335 | 56.424 | 1654.2 |
