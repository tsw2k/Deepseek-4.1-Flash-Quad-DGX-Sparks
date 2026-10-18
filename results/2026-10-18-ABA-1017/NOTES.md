# 2026-10-18: release vs DeepSeek-V4.1-Flash-1017, A/B/A; 1017 goes into production

07:13-08:56 Europe/Istanbul, `ops/night-levers.sh` with `DEADLINE=12:00`, 1017 queued as a lever
(`MODEL_DIR`, `MODEL_REVISION`, `MODEL_MANIFEST`, `ENGRAM_CACHE_DIR` overridden). Same image,
patch set, flags and env otherwise: measured set, L1, K5, 300K, and since this morning NCCL striped
over both rail-A PFs (`NCCL_IB_HCA=rocep1s0f1,roceP2p1s0f1`, the 2026-10-17 rail cutover; see
below). Kernel 7.0.0-1019 since 2026-10-17: none of these numbers compare with earlier results.
Every run cold after a relaunch; no client request during any of them; all three passed 10/10
gates and the 131K needle; long-context cold repetitions found nothing in the prefix cache.

| | A (01) | **1017 (02)** | A (03) | 1017 vs mean A |
|---|---|---|---|---|
| 150K cold time to first token, s | 79.8 | **81.1** | 79.2 | +2 % |
| 150K cold prefill, tok/s | 1,879 | **1,851** | 1,894 | -1 % |
| 150K warm next turn, time to first token, s | 1.88 | **1.90** | 1.90 | = |
| decode with 150K of context, tok/s | 50.6 | **48.7** | 50.5 | -4 % |
| cold prefill 8K / 32K / 64K target, tok/s | 1,824 / 1,852 / 1,821 | **1,806 / 1,855 / 1,830** | 1,804 / 1,829 / 1,832 | = |
| needle 131K prefill, tok/s | 1,774 | **1,793** | 1,784 | +1 % |
| C1 aggregate / per stream, tok/s | 49.35 / 55.3 | **50.48 / 56.1** | 51.64 / 58.5 | = (A spread 5 %) |
| C6 aggregate, tok/s | 157.1 | **163.2** | 152.8 | +5 % |
| DSpark draft acceptance (log average) | 52.3 % | **54.2 %** | 44.9 % | = |
| GSM8K, 250 | 98.4 % | **98.0 %** | 98.0 % | = |
| MMLU-Pro, 280 | 84.3 % | **85.7 %** | 84.3 % | +1.4 pt (4 answers) |
| completion tokens median, GSM8K / MMLU-Pro | 138 / 91 | **145 / 90.5** | 145.5 / 92 | = |

On speed, 1017 is the release: the architecture, config and kernels are the same, and every
difference sits inside the spread between the two baselines (C1 per stream varies 5 % from A to A).
On these two question sets the answers are as good: 245 vs 245-246 correct on GSM8K, 240 vs 236 on
MMLU-Pro, which at 280 questions is within noise. The claimed gains are in agentic and coding
work (Terminal-Bench, SWE, tool use), which these sets do not exercise; the claimed shorter
outputs do not show here, with thinking off and short answers.

The quality probe against `release-a` fails for 1017, as it must for different weights:

| corpus | ppl release / 1017 | top-1 agreement | KL mean |
|---|---|---|---|
| en-wiki | 2.809 / 2.840 | 0.904 | 0.127 |
| ru-wiki | 2.390 / 2.392 | 0.922 | 0.075 |
| code | 1.234 / 1.246 | 0.982 | 0.027 |

A shift of a fine-tune, perplexity within 1 % on the same text. The reference for probes from
now on is collected on 1017 itself (`/home/mtxc/dsv41-quality/1017-a`).

## Striping

The two baselines are also the first runs since the 2026-10-17 rail cutover put NCCL on both PFs
of cage B (92 to 182 Gbps NCCL). Against the last baselines before it (`2026-10-01-night-L13-batched16k`,
single PF, kernel 6.17), cold prefill at 150K went from ~1,710 to ~1,885 tok/s and a 150K cache
miss from 87-88 s to 79-80 s. Kernel and layout changed together, so the gain is not attributed to
striping alone.

## Production

After this run `cluster.env` was switched to 1017 (the release stays on disk; rollback is three
lines, in the comment there) and the fleet relaunched with `scripts/fleet up dsv41`.
