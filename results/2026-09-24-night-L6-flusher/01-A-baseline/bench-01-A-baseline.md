## 01-A-baseline (2026-09-23T23:07:19Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.46 | 55.52 | 0.299 |
| C2 | 76.7 | 43.28 | 0.343 |
| C3 | 97.4 | 37.24 | 0.386 |
| C4 | 116.43 | 34.15 | 0.419 |
| C5 | 134.37 | 31.25 | 0.422 |
| C6 | 151.57 | 29.49 | 0.457 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 75.68 | 57.06 | 56.18 | 50.82 | 44.04 | 42.3 |
| json | 50.18 | 39.93 | 31.67 | 31.86 | 26.97 | 28.54 |
| narrative | 30.99 | 24.01 | 18.5 | 17.19 | 15.26 | 14.33 |
| prose | 36.19 | 24.78 | 21.57 | 20.11 | 18.13 | 16.04 |
| math | 74.03 | 58.39 | 47.55 | 47.49 | 40.04 | 37.76 |
| reasoning | 62.45 | 43.63 | 36.67 | 32.51 | 29.0 | 27.15 |
| summary | 31.24 | 26.34 | 22.2 | 19.93 | 20.15 | 18.06 |
| format | 83.38 | 72.12 | 63.55 | 53.27 | 56.45 | 51.73 |
| ceiling_count | 88.94 | 78.59 | 70.84 | 62.87 | 60.3 | 55.92 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.944 | 1517.3 |
| 8000 | 11592 | 7.106 | 1631.3 |
| 32000 | 46810 | 27.948 | 1674.9 |
| 64000 | 93335 | 56.522 | 1651.3 |
