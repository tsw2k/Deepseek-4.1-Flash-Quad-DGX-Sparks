# Night of 2026-09-20: L3 applied, the new serving baseline measured

`@baseline` night: one cold relaunch with `SPEC_K=5 MAXLEN=300000` in cluster.env and one benchmark,
02:00-02:14 Europe/Istanbul. Gates 10/10, quality probe on the floor, watchdog re-armed, queue empty.
This run is the reference for everything measured from here on.

| | K3 / 600K baseline (mean of the three on 2026-09-19) | L3 as tested (2026-09-19) | **new baseline K5 / 300K** |
|---|---|---|---|
| C1 aggregate | 45.7 | 49.1 | **48.7** (+6.6 %) |
| C2 | 74.9 | 77.1 | 76.3 (+1.9 %) |
| C3 | 95.0 | 99.1 | 101.6 (+6.9 %) |
| C4 | 116.1 | 118.2 | 120.5 (+3.8 %) |
| C5 | 131.6 | 142.3 | 137.2 (+4.2 %) |
| C6 | 149.0 | 156.5 | 153.9 (+3.3 %) |
| C1 per-stream | 50.2 | 55.5 | **54.6** (+8.8 %) |
| prefill at 46,810 | 1,666 | 1,655 | 1,678 |
| needle 131K, s | 80.9 | 80.6 | 80.3 |
| DSpark acceptance | 2.97 | 3.67 | **3.71** |
| quality probe, en-wiki | top-1 0.990, KL 0.0033 | 0.989 / 0.0035 | 0.989 / 0.0033 |
| KV pool | 1.60-1.63M tokens (2.7 x 600K) | 1.60M | 1.58M tokens (**5.26 x 300K**) |

The gain holds outside the A/B/A that produced it: single-stream decode is 8.8 % faster than the K3
baseline and DSpark accepts 3.71 tokens a step instead of 2.97. Prefill, the 131K needle and the
next-token distribution are unchanged. The engine now refuses requests longer than 300K tokens and
holds 5.26 full-length requests in KV instead of 2.7.
