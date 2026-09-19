# Night of 2026-09-19: L3 (K5, 300K) and L5 (minimal patch set), A/B/A

First night run of `ops/night-levers.sh`: 02:00-03:29 Europe/Istanbul (23:00-00:29 UTC), five runs,
each after a relaunch (cold prefix cache) with every GPU at or below 60 C at the start. All five
passed the ten gates and the quality probe; the night ended on the baseline with the watchdog armed.
Runner log: `night.log`.

## Aggregate tok/s (eight categories), prefill, needle, acceptance

| run | C1 | C2 | C3 | C4 | C5 | C6 | C1 per-stream | prefill 46,810 | needle 131K, s | DSpark acceptance | KV pool, tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 A baseline | 45.4 | 74.4 | 94.9 | 115.8 | 134.4 | 152.2 | 50.0 | 1,661 | 80.7 | 2.97 | 1,600,568 |
| 02 **L3** K5 / 300K | 49.1 | 77.1 | 99.1 | 118.2 | 142.3 | 156.5 | **55.5** | 1,655 | 80.6 | **3.67** | 1,600,732 |
| 03 A baseline | 45.8 | 76.7 | 96.1 | 115.8 | 130.2 | 147.6 | 50.2 | 1,669 | 81.2 | 2.96 | 1,628,848 |
| 04 **L5** minimal | 45.4 | 75.1 | 95.6 | 114.7 | 136.5 | 155.1 | 50.0 | 1,685 | 80.7 | 2.98 | 1,519,538 |
| 05 A baseline | 45.9 | 73.5 | 94.1 | 116.6 | 130.2 | 147.2 | 50.5 | 1,669 | 80.9 | 2.98 | |

The three baselines agree within 1 % at C1 and 3 % at C6: this is the night's noise.

## L3: meets the acceptance rule

Against the mean of its two baselines (01, 03): C1 per-stream **+10.9 %**, C1 aggregate +7.7 %,
C5 +7.6 %, C6 +4.4 %; prefill -0.6 %, needle unchanged, gates 10/10, the quality probe on the floor
(en-wiki top-1 0.989, KL 0.0035). DSpark accepts 3.67 tokens a step instead of 2.96. That clears
the rule in LEVERS (C1 per-stream or C6 aggregate +5 %, prefill loss under 5 %, all gates).

What it costs is the maximum request length: 300K tokens instead of 600K. The KV pool is the same
size (1.60M tokens), so it holds 5.3 full-length requests instead of 2.7. Whether 300K is enough is
a product decision, not a benchmark result.

## L5: correct, not faster, and 6 % less KV

Against its baselines (03, 05): C1 -1 %, C6 +5 % (inside the night's 3 % spread plus run 01's
higher C6), prefill +1 %, gates 10/10, the probe on the floor. The minimal set boots and computes
the same distribution as the byte-identical measured set. Its KV pool is 1.52M tokens against
1.60-1.63M: it lacks 0xTank's graph startup changes. Not adopted as the default; what it proves is
that the recipe's own diffs are sound, which is what a move to a newer vLLM tree would start from.
