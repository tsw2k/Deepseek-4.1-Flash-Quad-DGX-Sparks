# 2026-10-20: 1017 vs 1017-abliterated, A/B/A; the abliterated checkpoint goes into production

Night 02:00-03:43 Europe/Istanbul, `ops/night-levers.sh` from the timer, the abliterated checkpoint
queued as a lever: `mrfakename/DeepSeek-V4.1-Flash-1017-abliterated` at 517efab9 (refusal subspace
projected out of `attn.wo_b` and `ffn.shared_experts.w2` in the 40 main layers; shards 3-42 differ
from 1017, everything else byte-identical, including the Engram shards, so the 1017 slices serve it
with `ENGRAM_REVISION`). Served as `deepseek-v4.1-flash-abliterated` and `deepseek-v4.1-flash`.
Same image, patches and flags as 1017 (measured set, L1, K5, 300K, NCCL striped over both rail-A
ports, telemetry off). Every run cold after a relaunch, no client request during any run, all
three passed 10/10 gates and the 131K needle; long-context cold repetitions found nothing cached.

| | 1017 (01) | **abliterated (02)** | 1017 (03) |
|---|---|---|---|
| GSM8K, 250 | 97.6 % | **97.2 %** | 97.2 % |
| MMLU-Pro, 280 | 84.3 % | **83.6 %** | 84.3 % |
| 150K cold time to first token, s | 80.3 | **79.5** | 80.1 |
| 150K cold prefill, tok/s | 1,868 | **1,886** | 1,871 |
| 150K warm next turn, s | 1.92 | **1.89** | 1.88 |
| decode with 150K of context, tok/s | 48.8 | **50.6** | 50.0 |
| needle 131K prefill, tok/s | 1,791 | **1,793** | 1,801 |
| C1 aggregate / per stream, tok/s | 50.2 / 55.9 | **50.3 / 56.9** | 49.5 / 55.2 |
| C6 aggregate, tok/s | 162.4 | **167.5** | 165.9 |
| DSpark draft acceptance (log average) | 54.7 % | **53.8 %** | 57.3 % |

On ordinary tasks the abliterated model answers as 1017 does: one GSM8K answer and two MMLU-Pro
answers fewer than the better 1017 run, inside the run-to-run spread. Speed is the same.

Quality probe against the 1017 reference (`1017-a`), which the abliterated weights are not
expected to match exactly:

| corpus | ppl 1017 / abliterated | top-1 agreement | KL mean |
|---|---|---|---|
| en-wiki | 2.842 / 2.844 | 0.955 | 0.027 |
| ru-wiki | 2.393 / 2.400 | 0.966 | 0.014 |
| code | 1.245 / 1.245 | 0.992 | 0.007 |

A small shift (en-wiki just past the probe's 0.96 top-1 threshold), a fifth of the shift between
the release and 1017 (KL 0.127 on en-wiki). Refusal behaviour was not measured here; the author
reports 4/100 chat and 9/100 thinking refusals against 97/98 for the base.

Switched in the morning with the user present: `cluster.env` on the operator host (spark-01,
`~/dsv41-src`) points at the abliterated directory, 1017 stays on disk for rollback, and a quality
reference is collected on the new weights.
