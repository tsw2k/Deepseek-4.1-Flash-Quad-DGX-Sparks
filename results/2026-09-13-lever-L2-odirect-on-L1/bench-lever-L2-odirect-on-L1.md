## lever-L2-odirect-on-L1 (2026-09-13T22:00:37Z)

set=measured-odirect k=3 maxlen=600000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 DSV41_ENGRAM_ODIRECT=1 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 45.0 | 49.52 | 0.295 |
| C2 | 71.16 | 39.95 | 0.348 |
| C3 | 94.15 | 35.18 | 0.39 |
| C4 | 111.01 | 31.25 | 0.428 |
| C5 | 126.37 | 28.51 | 0.423 |
| C6 | 141.97 | 26.79 | 0.477 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 65.23 | 48.47 | 46.07 | 40.06 | 38.74 | 36.51 |
| json | 44.18 | 37.7 | 31.45 | 29.67 | 27.52 | 24.97 |
| narrative | 35.15 | 24.98 | 21.16 | 19.12 | 17.32 | 15.68 |
| prose | 36.85 | 31.03 | 26.31 | 22.97 | 19.15 | 19.44 |
| math | 59.63 | 52.76 | 43.73 | 43.22 | 35.73 | 32.24 |
| reasoning | 53.54 | 40.6 | 34.93 | 31.17 | 27.05 | 25.36 |
| summary | 39.92 | 26.9 | 23.13 | 20.39 | 20.98 | 17.92 |
| format | 61.65 | 57.15 | 54.69 | 43.36 | 41.59 | 42.23 |
| ceiling_count | 68.82 | 58.04 | 55.97 | 52.59 | 49.08 | 47.43 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 2.17 | 1359.1 |
| 8000 | 11592 | 7.546 | 1536.3 |
| 32000 | 46810 | 30.422 | 1538.7 |
| 64000 | 93335 | 62.297 | 1498.2 |
