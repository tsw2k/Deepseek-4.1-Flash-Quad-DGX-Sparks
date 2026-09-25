## 02-L6-flusher (2026-09-23T23:25:57Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.27 | 55.72 | 0.309 |
| C2 | 78.14 | 44.36 | 0.341 |
| C3 | 94.05 | 35.78 | 0.387 |
| C4 | 112.58 | 32.26 | 0.43 |
| C5 | 130.29 | 30.36 | 0.461 |
| C6 | 142.36 | 27.84 | 0.473 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 77.64 | 62.25 | 52.41 | 46.14 | 45.42 | 39.64 |
| json | 58.38 | 44.95 | 34.11 | 33.78 | 28.11 | 27.48 |
| narrative | 29.33 | 21.99 | 18.65 | 15.5 | 14.83 | 13.69 |
| prose | 32.72 | 23.77 | 19.06 | 18.68 | 16.84 | 15.91 |
| math | 78.24 | 55.82 | 48.66 | 42.79 | 41.4 | 39.41 |
| reasoning | 53.18 | 40.49 | 35.33 | 29.97 | 27.84 | 23.89 |
| summary | 35.91 | 31.96 | 22.24 | 19.97 | 18.31 | 17.19 |
| format | 80.35 | 73.64 | 55.82 | 51.24 | 50.17 | 45.52 |
| ceiling_count | 88.86 | 75.89 | 69.43 | 62.08 | 57.45 | 53.14 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.935 | 1524.9 |
| 8000 | 11592 | 7.026 | 1649.9 |
| 32000 | 46810 | 29.495 | 1587.1 |
| 64000 | 93335 | 59.607 | 1565.9 |
