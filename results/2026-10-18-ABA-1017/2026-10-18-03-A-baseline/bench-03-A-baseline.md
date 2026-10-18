## 03-A-baseline (2026-10-18T05:30:26Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 NCCL_IB_HCA=rocep1s0f1,roceP2p1s0f1 NCCL_IB_ADDR_RANGE=10.77.0.0/16 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 51.64 | 58.5 | 0.297 |
| C2 | 79.52 | 45.5 | 0.342 |
| C3 | 99.56 | 39.21 | 0.363 |
| C4 | 120.28 | 35.3 | 0.406 |
| C5 | 144.0 | 33.15 | 0.416 |
| C6 | 152.77 | 29.87 | 0.466 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 77.04 | 69.87 | 59.8 | 49.3 | 45.94 | 42.53 |
| json | 66.69 | 40.02 | 40.52 | 35.08 | 29.1 | 28.61 |
| narrative | 30.46 | 22.89 | 19.67 | 17.4 | 15.33 | 15.06 |
| prose | 38.66 | 27.14 | 20.9 | 20.11 | 17.66 | 16.55 |
| math | 76.86 | 62.83 | 49.28 | 52.07 | 50.64 | 38.46 |
| reasoning | 60.86 | 43.61 | 35.81 | 32.76 | 29.4 | 30.39 |
| summary | 32.68 | 27.22 | 22.27 | 19.12 | 19.98 | 17.81 |
| format | 84.74 | 70.39 | 65.46 | 56.55 | 57.14 | 49.55 |
| ceiling_count | 90.84 | 79.81 | 72.61 | 63.79 | 60.44 | 57.3 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.846 | 1598.0 |
| 8000 | 11592 | 6.427 | 1803.7 |
| 32000 | 46810 | 25.587 | 1829.4 |
| 64000 | 93335 | 50.947 | 1832.0 |
