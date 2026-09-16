## L7-sysctls-repeat (2026-09-16T10:34:54Z)

set=measured k=3 maxlen=600000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 32.67 | 36.48 | 0.397 |
| C2 | 52.54 | 29.09 | 0.413 |
| C3 | 71.08 | 26.35 | 0.455 |
| C4 | 84.31 | 23.78 | 0.487 |
| C5 | 100.65 | 22.6 | 0.524 |
| C6 | 117.93 | 22.31 | 0.552 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 44.71 | 38.0 | 33.77 | 32.28 | 29.4 | 30.64 |
| json | 37.04 | 26.73 | 24.2 | 17.98 | 24.0 | 19.04 |
| narrative | 21.4 | 17.42 | 18.51 | 15.03 | 14.37 | 13.33 |
| prose | 24.46 | 20.01 | 18.96 | 17.71 | 16.73 | 16.06 |
| math | 42.46 | 35.12 | 32.19 | 28.61 | 31.31 | 28.98 |
| reasoning | 32.1 | 32.27 | 26.01 | 24.58 | 21.82 | 22.44 |
| summary | 28.65 | 23.75 | 20.38 | 17.93 | 7.41 | 16.66 |
| format | 60.99 | 39.39 | 36.77 | 36.12 | 35.77 | 31.33 |
| ceiling_count | 69.91 | 42.78 | 40.98 | 38.48 | 35.84 | 36.14 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 2.018 | 1461.8 |
| 8000 | 11592 | 7.049 | 1644.5 |
| 32000 | 46810 | 27.858 | 1680.3 |
| 64000 | 93335 | 57.717 | 1617.1 |
