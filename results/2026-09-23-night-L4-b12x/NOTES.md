# Night of 2026-09-23: L4 (b12x MXFP8 dense kernel) rejected on correctness

A/B/A, 02:00-02:42 Europe/Istanbul. Both baselines passed everything and matched the reference run
of 2026-09-20 (C1 per-stream 55.5 / 55.2 against 54.6, C6 151.8 / 153.7 against 153.9, acceptance
3.65 / 3.63 against 3.71). The night ended on the baseline with the watchdog armed.

## What the lever run did

The kernel was selected as intended: `run.txt` records `Using B12xMxfp8LinearKernel for MXFP8 GEMM`
for the dense linears and `Using EmulationMxfp8LinearKernel` for the BMM path (0xTank's compact
projection, unchanged). The engine booted in five minutes and then produced corrupted text. Five
of ten gates failed, so no benchmark was recorded:

| gate | result | detail |
|---|---|---|
| count | FAIL | a foreign token inside the sequence: `... 90 91敲门 91 92 ...` |
| greedy | FAIL | 1/5 identical, CJK characters in the output |
| prefill | FAIL | wrong recall: `902Fly` |
| tool | FAIL | function name corrupted: `get_是我们的weather` |
| vision | FAIL | `redanjingakon` for "red, green, blue" |
| identity, garble, prefill x4, json, thinking | pass | but the json gate's value reads `"The L座睡着 Musical和支持"`: it passes only because the gate checks structure |

The pattern is a dense projection that is right most of the time and wrong on some tokens: the
output stays on topic and keeps its structure while stray tokens from elsewhere in the vocabulary
appear. That is a numerics fault in this combination (b12x 1.3.0's `mxfp8_linear` on GB10 / sm_121,
vLLM 172d9a17's packing of this checkpoint's MXFP8 weights, or the two together), not a kernel
that is merely slower. Which of these it is was not investigated.

## Status

Rejected. The b12x package stays installed in `/var/tmp/dsv41-b12x` on the nodes; it is loaded only
when a run sets `EXTRA_PY_DIR`, which the serving configuration does not. The gates did what they
are for: this lever would have passed a throughput benchmark.
