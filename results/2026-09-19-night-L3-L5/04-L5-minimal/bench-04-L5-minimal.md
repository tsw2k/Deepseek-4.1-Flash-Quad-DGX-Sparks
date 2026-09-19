## 04-L5-minimal (2026-09-19T00:03:32Z)

set=minimal k=3 maxlen=600000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 45.44 | 49.96 | 0.289 |
| C2 | 75.12 | 42.0 | 0.324 |
| C3 | 95.58 | 35.97 | 0.376 |
| C4 | 114.7 | 32.61 | 0.388 |
| C5 | 136.5 | 30.73 | 0.418 |
| C6 | 155.08 | 29.48 | 0.467 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 66.11 | 51.21 | 46.65 | 40.52 | 41.72 | 41.38 |
| json | 44.41 | 44.66 | 33.04 | 31.19 | 27.54 | 26.49 |
| narrative | 34.98 | 25.84 | 21.1 | 18.2 | 17.87 | 16.35 |
| prose | 41.09 | 31.09 | 26.42 | 22.01 | 20.86 | 19.5 |
| math | 61.53 | 50.4 | 47.42 | 38.05 | 39.52 | 38.57 |
| reasoning | 53.5 | 43.73 | 34.95 | 36.22 | 29.15 | 27.4 |
| summary | 37.37 | 30.34 | 23.46 | 22.68 | 20.51 | 19.02 |
| format | 60.73 | 58.75 | 54.74 | 52.0 | 48.67 | 47.09 |
| ceiling_count | 66.92 | 59.87 | 57.16 | 53.92 | 51.07 | 46.44 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.97 | 1497.4 |
| 8000 | 11592 | 7.015 | 1652.4 |
| 32000 | 46810 | 27.777 | 1685.2 |
| 64000 | 93335 | 56.775 | 1644.0 |
