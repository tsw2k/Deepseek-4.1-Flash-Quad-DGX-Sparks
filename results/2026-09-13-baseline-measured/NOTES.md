# Baseline: measured configuration, first boot on the mtxc cluster

Recipe `a42df21`, patch set `measured`, vLLM `172d9a17`, image `sha256:389e58bbfe25`, DSpark K3,
600K max context, gmu 0.80, compact output projection on. 4x ASUS GX10, TP4, NCCL on rail A
only (Arista 7060CX, 100G passive DAC, `NCCL_IB_TC=106`, GID index 3 on every rank).

Host state: `glm53-flusher` and `glm53-fleet` stopped on all nodes; sysctls at defaults
(`vm.min_free_kbytes` 45155, `vm.watermark_scale_factor` 10); nothing else on the GPUs. GPU
clock burn before boot: 89.0-89.4 TFLOPS on all four (no latch). Boot to `/health`: 10 min.

Benchmark client on the head, against its rail A address. Tech2Wild's prompt set v1, unmodified.

## Against 0xTank's published run of the same configuration

| | this run | 0xTank (their 4x GB10) | delta |
|---|---:|---:|---:|
| C1 aggregate / per-stream decode, tok/s | 40.5 / 44.7 | 39.5 / 43.4 | +3 % |
| C4 aggregate, tok/s | 106.8 | 104.6 | +2 % |
| C6 aggregate, tok/s | 135.6 | 140.0 | -3 % |
| C1 coding per stream, tok/s | 63.4 | 63.0 | +1 % |
| cold prefill 11,592 / 46,810 / 93,335 tokens, tok/s | 1,609 / 1,632 / 1,527 | 1,440 / 1,635 / 1,353 | +12 % / 0 % / +13 % |
| needle, 130,258 tokens at 50 % | pass, 85.2 s | pass, 85.4 s | same answer |

Every cell is inside the ±5 % run-to-run spread upstream reports, except prefill at 12K and
93K, which ran faster here. **The measured configuration reproduces on this cluster.** One
single-rail 100G fabric matches their result, consistent with this cluster's earlier finding
that TP4 serving is not fabric-bound.

## Anomaly: the first prefill

The 2,950-token prefill took 6.2 s (476 tok/s); 0xTank measured 1.97 s. It was the first
unique-prefix prefill of that size after the concurrency suite, and the next three sizes were
normal. Likely a one-time cost (an autotune or graph path on first use), not a steady state.
Check on the next run by putting a throwaway prefill before the table.

## Gates

10/10. `greedy` is a measurement since `a42df21`: 4/5 identical this run, first divergence at
char 93 (the first attempt on this boot saw 3/5 at the same position, see
`../2026-09-13-baseline-measured-gates-attempt1/`). Divergent outputs are coherent and correct.
Lever L8 tests greedy draft sampling against it.

## DSpark

`spec-decode.log`: all 44 ten-second windows since boot (gates, benchmark, needle). Mean
acceptance length 2.99 (range 2.02-3.97) of a maximum 4 at K3; 65.6 % of drafted tokens
accepted (21,990 / 33,507). `bench/run.sh` wrote this file empty; it was re-captured from the
head's log afterwards.
