## 02-L10-engram64-longctx (2026-09-29T23:27:30Z)

set=measured k=5 maxlen=300000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 DSV41_ENGRAM_DISK_THREADS=64 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 48.25 | 54.07 | 0.312 |
| C2 | 74.99 | 42.59 | 0.34 |
| C3 | 100.74 | 38.7 | 0.375 |
| C4 | 122.78 | 35.73 | 0.392 |
| C5 | 137.41 | 31.53 | 0.428 |
| C6 | 156.57 | 30.13 | 0.475 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 75.79 | 56.38 | 51.53 | 53.21 | 44.69 | 41.45 |
| json | 46.0 | 37.42 | 38.97 | 32.01 | 28.11 | 27.3 |
| narrative | 29.11 | 22.49 | 19.21 | 17.44 | 16.37 | 14.06 |
| prose | 38.03 | 24.83 | 21.88 | 20.06 | 17.59 | 15.91 |
| math | 74.26 | 55.0 | 52.94 | 49.78 | 41.45 | 42.01 |
| reasoning | 61.07 | 44.8 | 36.53 | 32.47 | 30.19 | 27.59 |
| summary | 30.98 | 27.7 | 23.26 | 21.65 | 19.01 | 17.64 |
| format | 77.33 | 72.07 | 65.24 | 59.19 | 54.84 | 55.08 |
| ceiling_count | 88.25 | 78.68 | 66.62 | 62.68 | 60.43 | 56.28 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.895 | 1556.9 |
| 8000 | 11592 | 6.718 | 1725.6 |
| 32000 | 46810 | 26.832 | 1744.6 |
| 64000 | 93335 | 54.826 | 1702.4 |
