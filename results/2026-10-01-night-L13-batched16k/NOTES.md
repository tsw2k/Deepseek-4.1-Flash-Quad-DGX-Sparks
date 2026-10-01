# Night 2026-10-01: L13, prefill chunk 16384 tokens (`MAX_BATCHED=16384`, 8192 by default)

02:00-03:00 Europe/Istanbul (23:00-24:00 UTC on 09-30, hence the run directories' date), A/B/A,
every run after a cold relaunch at or below 60 C.

- Quiet gate: no client before any relaunch, no wait; `client requests during this run: 0` in all
  three runs.
- Gates 10/10, quality probe 3/3 within thresholds, needle 131K passed, in all three runs.
- Long-context runs: cold repetitions 0 cached tokens, warm 149,760, in all three.
- Memory guard (enforce, 6 GiB): no trip. Lowest MemAvailable on the head during boot: 11.1 GiB
  (A), **9.8 GiB (L13)**, 11.2 GiB (A).
- Ended on the baseline, health 200, watchdog re-armed, 119 min before the deadline.

| | A (01) | L13 (02) | A (03) | L13 vs mean A |
|---|---|---|---|---|
| **150K cold time to first token, s** | 87.80 | 87.55 | 87.90 | -0.3 % |
| **150K cold prefill, tok/s** | 1,708 | 1,713 | 1,706 | +0.3 % |
| 150K warm next turn, time to first token, s | 2.05 | 2.01 | 2.05 | = |
| decode with 150K of context, tok/s | 47.3 | 48.8 | 50.2 | = |
| needle 131K prefill, tok/s | 1,628 | 1,591 | 1,629 | -2.3 % |
| cold prefill 64K / 32K / 8K target, tok/s | 1,655 / 1,676 / 1,604 | 1,626 / 1,660 / 1,654 | 1,656 / 1,685 / 1,591 | -1.8 / -1.2 / +3.5 % |
| C1 aggregate / per stream, tok/s | 48.45 / 54.74 | 50.40 / 56.84 | 49.15 / 54.89 | +3.4 / +3.7 % |
| C6 aggregate, tok/s | 150.9 | 149.3 | 158.7 | -3.4 % |
| **KV cache, tokens** | 1,570,809 | **640,229** | 1,670,250 | **-60 %** |

The KV cache size is from each engine's log (`Available KV cache memory` 7.4 / 4.1 / 7.95 GiB).
`cluster.sh down` names its log directory after the time of the stop, so the log of a run sits in
the directory of the next one.

## Reading

Prefill of these prompts is not limited by the chunk size: at 150K a 16K chunk changes the time to
first token by a quarter of a second out of 88, and at 64-131K it is 1-2 % slower. vLLM's startup
profile runs a full chunk, so the activation peak doubles and the engine sizes its KV cache after
it: 3.3 GiB less on every rank, 60 % fewer tokens, five 300K requests down to two. The guard's head
floor dropped by 1.4 GiB for the same reason.

C1 +3.7 % is outside the two baselines' spread but below the rule's +5 %, and C6 moved the other way.

Not adopted: no gain on the measure that matters for this traffic, and a large loss of KV cache.
