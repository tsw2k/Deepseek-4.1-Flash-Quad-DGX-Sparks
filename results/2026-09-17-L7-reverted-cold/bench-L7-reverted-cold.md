## L7-reverted-cold (2026-09-17T18:33:30Z)

set=measured k=3 maxlen=600000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 46.25 | 50.85 | 0.284 |
| C2 | 72.49 | 41.07 | 0.343 |
| C3 | 92.85 | 34.89 | 0.381 |
| C4 | 117.43 | 33.11 | 0.389 |
| C5 | 133.28 | 30.06 | 0.419 |
| C6 | 146.58 | 27.54 | 0.472 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 66.16 | 54.6 | 45.67 | 43.76 | 41.45 | 37.03 |
| json | 50.15 | 36.03 | 35.95 | 29.51 | 28.01 | 24.61 |
| narrative | 34.72 | 26.88 | 21.93 | 19.96 | 17.26 | 17.05 |
| prose | 40.09 | 29.43 | 25.29 | 23.88 | 20.31 | 19.15 |
| math | 62.15 | 52.25 | 47.11 | 42.4 | 37.85 | 34.27 |
| reasoning | 57.22 | 42.44 | 36.91 | 32.2 | 29.29 | 28.02 |
| summary | 33.69 | 27.19 | 22.22 | 22.38 | 20.43 | 18.63 |
| format | 62.64 | 59.73 | 44.03 | 50.77 | 45.88 | 41.52 |
| ceiling_count | 69.15 | 59.41 | 57.09 | 53.7 | 49.62 | 48.5 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 1.998 | 1476.8 |
| 8000 | 11592 | 7.175 | 1615.6 |
| 32000 | 46810 | 28.522 | 1641.2 |
| 64000 | 93335 | 56.783 | 1643.7 |
