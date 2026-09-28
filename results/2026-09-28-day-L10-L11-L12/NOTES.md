# L10, L11, L12 (2026-09-28, daytime A/B/A under the memory guard)

`ops/night-levers.sh` started by hand at 16:34 UTC with three levers on the serving configuration
(release, K5, 300K, L1, guard enforce at 6 GiB). Every run was cold (relaunch, GPUs at or below
60 C). All runs that booted passed the gates and the quality probe (en-wiki top-1 0.989-0.990).

| run | C1 | C3 | C5 | C6 | C1 per-stream | prefill 2,950 / 46,810 / 93,335 | needle 131K, s | acceptance |
|---|---|---|---|---|---|---|---|---|
| 01 A | 49.9 | 95.3 | 133.2 | 152.5 | 56.1 | 1,540 / 1,690 / 1,663 | 80.0 | 3.66 |
| 02 **L10** Engram 64 threads | 49.9 | 96.6 | 134.9 | 150.8 | 56.0 | **1,614 / 1,733 / 1,698** | 78.1 | 3.64 |
| 03 A | 50.4 | 102.1 | 135.5 | 151.2 | 56.5 | 1,488 / 1,671 / 1,663 | 79.7 | 3.72 |
| (L11 K7 did not boot) | | | | | | | | |
| 04 A | 49.3 | 95.8 | 141.9 | 152.3 | 55.3 | 1,528 / 1,672 / 1,656 | 80.1 | 3.71 |
| 05 **L12** async scheduling | 48.9 | 101.3 | 136.4 | 157.2 | 54.7 | 1,490 / 1,681 / 1,657 | 79.5 | 3.64 |
| 06 A | 49.3 | 101.2 | 141.8 | 152.3 | 54.9 | 1,487 / 1,687 / 1,657 | 80.1 | 3.69 |

## L10: `DSV41_ENGRAM_DISK_THREADS=64` (32 by default)

Against its baselines (01, 03): decode unchanged (C1 per-stream -0.8 %, C6 -0.7 %); cold prefill
+6.6 % at 2,950 tokens, +3.1 % at 46,810, +2.1 % at 93,335; the needle 2 % faster. Below the
acceptance rule (C1 per-stream or C6 +5 %), so not adopted. It is the one lever that moved
prefill the right way on this cluster; if prefill-heavy traffic ever matters more than decode,
it is the first to revisit.

## L11: DSpark K7 — not possible

Every worker refused the configuration before loading: `num_speculative_tokens:7 must be divisible
by n_predict=5` (`L11-k7-worker.log`). The DSpark draft predicts five tokens a pass; vLLM accepts K
up to 5 or a multiple of it. K5, the serving value, is therefore the largest single draft pass; K10
means two passes a step with the second five positions at low acceptance.

## L12: `--async-scheduling`

Against its baselines (04, 06): C6 +3.2 %, C3 +2.8 %, C5 -3.8 %, C1 per-stream -0.7 %; prefill and
needle unchanged. Mixed, and inside the day's spread (C5 across the four baselines: 133-142).
Not adopted. It does boot and run with DSpark on this stack, which was the open question.
