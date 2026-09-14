## exl3-3p5bpw (2026-09-14T23:10:22Z)

set=exl3-tp3e k=3 maxlen=600000 gmu=0.80 lever_env=NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8 draft=probabilistic spec=dspark

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 52.27 | 56.69 | 0.232 |
| C2 | 87.37 | 48.53 | 0.262 |
| C3 | 115.2 | 43.44 | 0.326 |
| C4 | 140.07 | 39.78 | 0.359 |
| C5 | 160.7 | 36.97 | 0.402 |
| C6 | 180.33 | 34.51 | 0.415 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 72.32 | 65.16 | 59.46 | 58.77 | 57.52 | 49.52 |
| json | 66.07 | 57.87 | 44.95 | 45.13 | 38.35 | 32.8 |
| narrative | 37.56 | 30.15 | 25.59 | 25.24 | 21.8 | 19.99 |
| prose | 39.85 | 35.48 | 31.34 | 27.08 | 24.1 | 24.7 |
| math | 62.78 | 56.47 | 48.46 | 43.22 | 43.32 | 43.78 |
| reasoning | 63.05 | 49.85 | 44.88 | 38.98 | 38.45 | 38.15 |
| summary | 40.4 | 32.35 | 30.44 | 28.65 | 27.85 | 23.18 |
| format | 71.48 | 60.91 | 62.37 | 51.21 | 44.4 | 43.98 |
| ceiling_count | 77.38 | 72.12 | 66.72 | 59.66 | 56.01 | 54.61 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 2.057 | 1433.9 |
| 8000 | 11592 | 7.832 | 1480.2 |
| 32000 | 46810 | 31.44 | 1488.9 |
| 64000 | 93335 | 62.488 | 1493.7 |
