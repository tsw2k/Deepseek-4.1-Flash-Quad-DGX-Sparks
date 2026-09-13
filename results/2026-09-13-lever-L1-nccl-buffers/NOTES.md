# Lever L1: NCCL connection buffers

Baseline plus `LEVER_ENV="NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8"`
(MiaAI's settings for SGLang TP3, applied unchanged). Started with `scripts/fleet up dsv41`.

**Accepted.**

| | baseline | L1 | change |
|---|---:|---:|---:|
| C1 aggregate / per-stream decode, tok/s | 40.5 / 44.7 | 46.1 / 50.7 | +14 % / +13 % |
| C2 aggregate | 57.5 | 73.1 | +27 % |
| C3 aggregate | 79.1 | 95.8 | +21 % |
| C4 aggregate | 106.8 | 112.8 | +6 % |
| C5 aggregate | 105.9 | 132.6 | +25 % |
| C6 aggregate / per-stream | 135.6 / 25.9 | 151.0 / 28.5 | +11 % / +10 % |
| mean TTFT C1 / C6, s | 0.358 / 0.515 | 0.282 / 0.443 | -21 % / -14 % |
| cold prefill 2,950 / 11,592 / 46,810 / 93,335 tokens, tok/s | 476 / 1,609 / 1,632 / 1,527 | 1,441 / 1,622 / 1,665 / 1,654 | first-prefill anomaly gone; +2 % at 47K; +8 % at 93K |
| needle 130K | pass, 85.2 s | pass, 80.1 s | |
| MemAvailable while serving | 4-6 GiB | 14-16 GiB | about +10 GiB per node |
| gates | 10/10 | 10/10 (greedy 2/5) | |

Acceptance rule (C1 per-stream or C6 aggregate +5 % or more, prefill at 47K no worse than
-5 %, gates pass): met on both throughput criteria, well beyond the ±5 % run-to-run spread.
One run each; repeat before publishing the numbers as final.

Why it helps, as far as the data goes: NCCL's default connection buffers are pinned host
memory, which on GB10 is the GPU pool. MiaAI measured 4.7 GiB pinned per node cut to 0.14 GiB;
here MemAvailable rose by about 10 GiB per node. Throughput gains are largest at C2-C5, where
batches grow and memory pressure used to bite. The first-prefill anomaly of the baseline
(2,950 tokens at 476 tok/s) did not recur.

Caveat: the LiteLLM proxy on spark-01 reaches vLLM from the same address as the benchmark
client, so client requests cannot be told apart by source. The head logged 247 completions in
the 25 minutes around the run, about what gates plus the benchmark send.
