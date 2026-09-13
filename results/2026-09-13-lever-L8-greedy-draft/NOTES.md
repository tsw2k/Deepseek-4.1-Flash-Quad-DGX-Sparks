# Lever L8: greedy DSpark draft sampling

Hypothesis: temperature-0 outputs diverge because probabilistic draft sampling changes the
verify-window shapes per request, hence the kernels, hence the logits.

Configuration: baseline plus `DRAFT_SAMPLE=greedy` (container label `dsv41.draft_sample=greedy`).

Result: **rejected**. Determinism did not improve.

| | baseline, probabilistic draft | L8, greedy draft |
|---|---|---|
| `greedy` gate, identical of 5 | 4/5, 3/5, 2/5 on three runs | 1/5 |
| 10 identical requests, distinct texts | not measured (6 requests: 2 texts) | 3 texts (7/2/1) |
| logprob of " These" at char 92 across runs | -0.57 to -1.77 | -0.07 to -1.25 |

(`logprobs-pos92-10runs.txt`.) The target's own distribution at a fixed position, with an
identical preceding text, moves by up to ~2.7 nats between identical requests. That is not a
rounding-level near tie, and random drafting is not its source.

Gates 10/10. Mean acceptance length stayed in the same range (2.87-3.54). No benchmark
run: the lever was only about determinism.

Also observed in both configurations: the differences between the top-3 logprobs are always
exact multiples of 0.25, which suggests logits on a 0.25 grid somewhere in the head or the
logprob path. Not explained; worth checking separately.

Next test to isolate the cause: speculative decoding off entirely. If outputs still diverge,
the source is the target's kernels or MoE routing, not speculation.

## Independent corroboration

AtomicChat measured the original checkpoint on 4x B200, vLLM `e47aa780`, **no speculative
decoding**: two runs disagree with each other on 4 % of top-1 tokens (KL 0.016 on general
text), and a batch-size-1 run disagrees about as much, which argues against batching. Their
working hypothesis is non-deterministic MoE kernels flipping near-tied experts
([model card](https://huggingface.co/AtomicChat/DeepSeek-V4.1-Flash-NVFP4-nvidia)). That fits
this result: temperature-0 divergence is a property of the target's MoE compute on this
model, not of DSpark.

## Afterwards

Reverted to `probabilistic` with `scripts/fleet down dsv41 && scripts/fleet up dsv41`
(mtxc-spark-cluster), boot 5 min, watchdog re-armed, gates 10/10
(`../2026-09-13-restored-probabilistic/gates.json`, greedy 2/5).
