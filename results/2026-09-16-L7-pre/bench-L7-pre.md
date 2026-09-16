## L7-pre (2026-09-16T09:50:12Z)

set=measured k=3 maxlen=600000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 45.35 | 49.79 | 0.289 |
| C2 | 74.5 | 41.7 | 0.338 |
| C3 | 95.25 | 35.61 | 0.362 |
| C4 | 115.37 | 32.38 | 0.388 |
| C5 | 130.5 | 29.38 | 0.417 |
| C6 | 150.27 | 28.5 | 0.481 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 65.44 | 58.46 | 46.93 | 41.19 | 40.71 | 42.09 |
| json | 44.45 | 35.0 | 31.7 | 29.95 | 28.71 | 26.0 |
| narrative | 35.49 | 27.88 | 22.66 | 19.48 | 17.99 | 17.08 |
| prose | 39.37 | 28.28 | 24.33 | 23.17 | 20.76 | 19.03 |
| math | 62.64 | 49.96 | 48.77 | 43.13 | 38.07 | 34.87 |
| reasoning | 52.81 | 43.45 | 35.86 | 31.22 | 27.1 | 27.58 |
| summary | 35.09 | 29.04 | 27.16 | 22.15 | 19.16 | 19.43 |
| format | 63.04 | 61.57 | 47.47 | 48.79 | 42.5 | 41.93 |
| ceiling_count | 70.1 | 59.29 | 56.83 | 53.29 | 48.61 | 46.29 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.941 | 1519.8 |
| 8000 | 11592 | 6.916 | 1676.1 |
| 32000 | 46810 | 27.687 | 1690.7 |
| 64000 | 93335 | 56.816 | 1642.8 |
