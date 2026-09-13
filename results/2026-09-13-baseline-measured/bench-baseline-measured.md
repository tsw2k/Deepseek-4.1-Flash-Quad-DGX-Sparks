## baseline-measured (2026-09-13T17:00:08Z)

set=measured k=3 maxlen=600000 gmu=0.80 lever_env=none

Prompt set `v1` (identical across boots), temperature 0, thinking off. Tokens from the server's usage block; TTFT = first token delta.

### Throughput by concurrency (8 categories; the counting ceiling is excluded)

| C | aggregate tok/s | per-stream tok/s | mean TTFT (s) |
|---|---|---|---|
| C1 | 40.51 | 44.73 | 0.358 |
| C2 | 57.52 | 32.84 | 0.483 |
| C3 | 79.13 | 30.53 | 0.527 |
| C4 | 106.83 | 30.07 | 0.472 |
| C5 | 105.87 | 23.6 | 0.582 |
| C6 | 135.57 | 25.85 | 0.515 |

### Per-stream tok/s by category

| category | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| coding | 63.41 | 45.62 | 36.75 | 43.52 | 27.11 | 35.24 |
| json | 38.02 | 28.48 | 24.87 | 28.3 | 18.31 | 24.53 |
| narrative | 23.89 | 17.9 | 16.2 | 13.43 | 13.73 | 16.49 |
| prose | 28.41 | 20.75 | 18.42 | 17.3 | 20.37 | 19.28 |
| math | 62.32 | 41.83 | 34.39 | 40.07 | 34.49 | 28.35 |
| reasoning | 58.15 | 38.69 | 32.84 | 32.52 | 28.07 | 22.77 |
| summary | 36.6 | 21.82 | 25.82 | 21.17 | 18.18 | 19.81 |
| format | 47.05 | 47.61 | 54.92 | 44.27 | 28.54 | 40.3 |
| ceiling_count | 50.3 | 62.78 | 56.45 | 50.65 | 34.7 | 46.66 |

### Cold prefill (unique prefix)

| target | prompt tokens | TTFT (s) | prefill tok/s |
|---|---|---|---|
| 2000 | 2950 | 6.197 | 476.0 |
| 8000 | 11592 | 7.206 | 1608.6 |
| 32000 | 46810 | 28.689 | 1631.6 |
| 64000 | 93335 | 61.113 | 1527.3 |
