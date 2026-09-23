## 03-A-baseline (2026-09-22T23:34:25Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.2 | 55.17 | 0.315 |
| C2 | 78.49 | 44.53 | 0.342 |
| C3 | 94.34 | 36.47 | 0.384 |
| C4 | 117.31 | 33.7 | 0.416 |
| C5 | 133.96 | 30.75 | 0.426 |
| C6 | 153.66 | 29.64 | 0.455 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 75.25 | 61.73 | 51.65 | 46.36 | 44.53 | 45.55 |
| json | 45.01 | 43.8 | 33.3 | 30.35 | 28.05 | 27.79 |
| narrative | 33.59 | 23.38 | 17.72 | 17.01 | 15.47 | 14.05 |
| prose | 37.14 | 26.73 | 21.88 | 20.47 | 17.33 | 16.67 |
| math | 76.02 | 68.07 | 48.19 | 54.55 | 40.47 | 38.97 |
| reasoning | 60.67 | 40.6 | 37.92 | 31.2 | 28.69 | 27.04 |
| summary | 37.16 | 27.54 | 22.96 | 18.96 | 19.03 | 17.36 |
| format | 76.56 | 64.42 | 58.11 | 50.73 | 52.42 | 49.66 |
| ceiling_count | 88.86 | 77.36 | 66.77 | 62.36 | 59.01 | 56.21 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.942 | 1519.0 |
| 8000 | 11592 | 7.203 | 1609.4 |
| 32000 | 46810 | 28.477 | 1643.8 |
| 64000 | 93335 | 56.891 | 1640.6 |
