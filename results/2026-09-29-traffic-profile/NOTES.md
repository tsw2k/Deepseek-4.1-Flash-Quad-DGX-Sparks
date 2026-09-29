# What the proxy actually served (LiteLLM spend log, 2026-09-13 to 2026-09-29)

Aggregates only, from `LiteLLM_SpendLogs` (`traffic.sql`): timestamps, token counts, status. No
request or response content was read.

## Volume

247 requests to `deepseek-v4.1-flash` from 3 keys, 26 of them failed. Real use came in three bursts:
2026-09-16 00:00-01:00 UTC (107 requests), 2026-09-16 10:00-12:00 UTC (100), 2026-09-17
17:00-19:00 UTC (36). Nothing since 2026-09-17. The failures line up with daytime relaunches for
lever measurements: 15 at 10:13 UTC on 09-16, 11 on 09-17 during the L7 runs.

## Shape

| | p50 | p90 | p99 | max |
|---|---|---|---|---|
| prompt tokens | 146,692 | 177,569 | 187,789 | 189,086 |
| completion tokens | 427 | 1,925 | 8,629 | 9,483 |
| time to first token, s | 1.18 | 10.9 | 63.0 | |
| request duration, s | 9.9 | 41.9 | | |

91 % of requests carry 100K tokens or more of prompt and get a short answer: an agent with a long,
growing context. The low median time to first token with a 147K prompt is the prefix cache; the
p90/p99 are cache misses paying a full prefill at ~1,650 tok/s. Decode per request, median 58 tok/s.

Concurrency, time-weighted while anything was in flight: one request 97.1 % of the time, two 2.9 %,
never more.

## What it means for tuning

- C5/C6 throughput, what most levers were judged on, did not occur. Single-stream decode and, above
  all, cold prefill of 100-190K-token prompts (the cache misses) are what users wait for.
- L10 (64 Engram read threads) improved exactly that, cold prefill by 2-7 %, and was set aside only
  because the acceptance rule looks at decode. For this workload it is worth taking.
- 300K per request covers everything seen (largest prompt 189K).
- The busiest hour so far, 00 UTC, is 03:00 Europe/Istanbul: inside the night lever window.
