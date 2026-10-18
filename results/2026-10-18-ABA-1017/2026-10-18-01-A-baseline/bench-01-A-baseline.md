## 01-A-baseline (2026-10-18T04:21:04Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 NCCL_IB_HCA=rocep1s0f1,roceP2p1s0f1 NCCL_IB_ADDR_RANGE=10.77.0.0/16 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 49.35 | 55.27 | 0.298 |
| C2 | 83.37 | 47.26 | 0.335 |
| C3 | 103.1 | 39.36 | 0.361 |
| C4 | 122.56 | 35.75 | 0.405 |
| C5 | 139.5 | 32.12 | 0.444 |
| C6 | 157.09 | 30.62 | 0.435 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 79.14 | 65.65 | 54.18 | 52.09 | 45.15 | 44.41 |
| json | 47.62 | 44.12 | 38.33 | 34.47 | 34.47 | 29.27 |
| narrative | 31.03 | 24.11 | 19.37 | 16.67 | 15.12 | 14.97 |
| prose | 33.31 | 25.55 | 21.58 | 19.98 | 17.48 | 17.08 |
| math | 77.95 | 70.25 | 52.98 | 49.01 | 41.37 | 39.34 |
| reasoning | 60.73 | 46.46 | 36.48 | 31.09 | 31.01 | 28.13 |
| summary | 30.81 | 24.62 | 25.15 | 21.18 | 17.89 | 16.78 |
| format | 81.56 | 77.28 | 66.83 | 61.5 | 54.51 | 54.96 |
| ceiling_count | 92.45 | 79.65 | 71.5 | 64.38 | 60.45 | 57.26 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.84 | 1603.5 |
| 8000 | 11592 | 6.356 | 1823.7 |
| 32000 | 46810 | 25.274 | 1852.1 |
| 64000 | 93335 | 51.246 | 1821.3 |
