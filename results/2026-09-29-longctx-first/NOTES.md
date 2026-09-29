# First long-context timings on the serving configuration

2026-09-29 ~18:30 UTC, `bench/longctx.py --reps 1` against production (release, measured set, L1,
L3: K5 / 300K), no relaunch in front of it: the engine had been up since 2026-09-28 17:59 with no
client traffic, so its page cache was warm, as it is when a real client misses the prefix cache.
The cold request found nothing in the prefix cache (0 hit tokens), so it is a true miss. Corpus:
the quality code corpus, SHA-256 matching `2026-09-14-quality-reference-release/corpus-SHA256SUMS`.

| | prompt tokens | cached | time to first token | prefill | decode, 256 tokens |
|---|---|---|---|---|---|
| cold turn | 149,947 | 0 | 89.0 s | 1,684 tok/s | 44.6 tok/s |
| warm next turn (+2K) | 152,212 | 149,760 | 2.04 s | 1,204 tok/s (new tokens) | 43.8 tok/s |

- A prefix-cache miss at the proxy's median prompt costs a minute and a half before the first token;
  a hit costs two seconds. The proxy's p99 of 63 s (`2026-09-29-traffic-profile`) is this, on
  somewhat shorter prompts or partial hits.
- Decode with 150K of context behind it is 44-45 tok/s, against 54.6 per stream on the short C1
  prompts of the fixed benchmark: the long context costs about a fifth of decode speed.
- Cold prefill at 150K runs at the same rate as the fixed benchmark's 47K point (~1,678 tok/s), so
  prefill throughput holds flat over this range; the time to first token scales with the prompt.

One repetition, one run: the reference for levers is the first night run with the scenario in
`bench/run.sh` (two repetitions, after a relaunch, read against its A/B/A baselines).
