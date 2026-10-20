## 02-L1017abl-517efab9 (2026-10-19T23:42:27Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 NCCL_IB_HCA=rocep1s0f1,roceP2p1s0f1 NCCL_IB_ADDR_RANGE=10.77.0.0/16 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 50.3 | 56.9 | 0.308 |
| C2 | 80.79 | 46.95 | 0.337 |
| C3 | 103.15 | 40.13 | 0.393 |
| C4 | 126.05 | 36.52 | 0.393 |
| C5 | 148.15 | 34.49 | 0.42 |
| C6 | 167.49 | 32.65 | 0.442 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 76.92 | 65.42 | 61.76 | 55.96 | 56.98 | 51.78 |
| json | 61.63 | 49.27 | 41.7 | 39.94 | 42.51 | 34.27 |
| narrative | 31.59 | 25.99 | 18.83 | 18.49 | 15.91 | 14.76 |
| prose | 41.01 | 27.92 | 26.71 | 23.42 | 20.6 | 19.85 |
| math | 62.95 | 54.52 | 50.34 | 43.11 | 43.08 | 40.28 |
| reasoning | 55.53 | 45.32 | 40.5 | 36.9 | 30.93 | 31.14 |
| summary | 38.37 | 30.01 | 24.87 | 21.43 | 20.08 | 17.74 |
| format | 87.18 | 77.16 | 56.32 | 52.87 | 45.81 | 51.34 |
| ceiling_count | 90.69 | 79.77 | 73.42 | 70.22 | 65.69 | 62.54 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.845 | 1599.0 |
| 8000 | 11592 | 6.72 | 1725.1 |
| 32000 | 46810 | 25.215 | 1856.5 |
| 64000 | 93335 | 51.257 | 1820.9 |
