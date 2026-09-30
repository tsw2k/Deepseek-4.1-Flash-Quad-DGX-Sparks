# Night 2026-09-30: L10 (64 Engram read threads), read on the long-context timings

02:00-02:58 Europe/Istanbul (23:00-23:58 UTC on 09-29, hence the run directories' date), A/B/A, each
run after a cold relaunch with the GPUs at or below 60 C. The first night with the client-quiet gate
and with `bench/longctx.py` in every run.

- Quiet gate: no client in the 15 minutes before any of the three relaunches, no wait. `client
  requests during this run: 0` in all three runs.
- Gates 10/10 and the quality probe within thresholds (3/3 corpora) in all three runs; needle 131K
  passed in all three.
- Long-context runs: both cold repetitions of every run found 0 tokens in the prefix cache, both warm
  ones 149,760 (`cold_runs_that_hit_the_cache` empty).
- Ended on the baseline, health 200, watchdog re-armed, 121 min before the deadline.

| | A (01) | L10 (02) | A (03) | L10 vs mean A |
|---|---|---|---|---|
| **150K cold time to first token, s** | 87.15 | 86.64 | 88.07 | -1.1 % |
| **150K cold prefill, tok/s** | 1,721 | 1,731 | 1,703 | +1.1 % |
| 150K warm next turn, time to first token, s | 2.02 | 2.05 | 2.06 | = |
| decode with 150K of context, tok/s | 49.3 | 50.1 | 49.2 | +1.6 % |
| needle 131K prefill, tok/s | 1,628 | 1,668 | 1,630 | +2.4 % |
| cold prefill 64K target (93K tokens), tok/s | 1,654 | 1,702 | 1,656 | +2.9 % |
| cold prefill 32K target (47K tokens), tok/s | 1,687 | 1,745 | 1,684 | +3.5 % |
| C1 aggregate / per stream, tok/s | 49.27 / 55.2 | 48.25 / 54.07 | 49.30 / 55.09 | -2.1 % / -2.0 % |
| C6 aggregate, tok/s | 149.5 | 156.6 | 151.6 | +4.0 % |

Each longctx figure is the median of two repetitions; the repetitions of one run sit within 3 s of
each other, and the two baselines within 1 s.

## Reading

L10 repeats the day run of 2026-09-28: cold prefill a few percent faster at 47-130K tokens. At the
prompt size the proxy actually serves (150K) the gain shrinks to 1 %, one second out of 87, which is
the size of the gap between the two baselines. The prefill of these prompts is bound by compute, not
by Engram reads from NVMe; more readers help the shorter prompts, where the reads are a larger share
of the work.

C1 is 2 % lower, outside the two baselines' spread (0.1 %); C6 is 4 % higher, below the rule's +5 %.

Not adopted: by the rule (no +5 % at C1 or C6), and by the measure that matters here, since a
cache miss still costs about 87 s with or without it. It does no harm to quality, so it can come back
if the traffic moves to shorter prompts or more streams.

The baselines are the reference for later long-context comparisons on this configuration (release,
measured set, L1, K5, 300K): cold time to first token 87-88 s at 150K, warm 2.0 s, decode 49 tok/s
with the context behind it. The first reading (`2026-09-29-longctx-first`, 44.6 tok/s decode) came
from an engine that had been up for a day; after a relaunch decode at 150K is 49 tok/s.
