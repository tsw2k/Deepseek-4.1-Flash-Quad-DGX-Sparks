## 03-A-baseline (2026-09-23T23:44:10Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 48.3 | 53.81 | 0.307 |
| C2 | 73.52 | 42.58 | 0.346 |
| C3 | 97.61 | 37.23 | 0.372 |
| C4 | 112.64 | 32.45 | 0.398 |
| C5 | 141.67 | 32.75 | 0.425 |
| C6 | 151.16 | 29.5 | 0.486 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 79.95 | 57.62 | 55.05 | 44.84 | 48.85 | 41.37 |
| json | 47.17 | 40.4 | 30.1 | 29.61 | 27.0 | 30.47 |
| narrative | 30.69 | 21.85 | 18.34 | 17.21 | 15.07 | 14.93 |
| prose | 32.17 | 26.84 | 21.25 | 19.03 | 18.17 | 16.28 |
| math | 73.83 | 55.25 | 49.95 | 43.86 | 46.5 | 38.88 |
| reasoning | 60.58 | 44.07 | 35.1 | 32.7 | 28.91 | 28.19 |
| summary | 31.91 | 25.95 | 22.45 | 19.16 | 17.7 | 16.94 |
| format | 74.16 | 68.65 | 65.6 | 53.15 | 59.77 | 48.98 |
| ceiling_count | 90.14 | 78.8 | 69.52 | 62.07 | 63.88 | 55.53 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.962 | 1503.6 |
| 8000 | 11592 | 7.029 | 1649.1 |
| 32000 | 46810 | 27.903 | 1677.6 |
| 64000 | 93335 | 56.803 | 1643.1 |
