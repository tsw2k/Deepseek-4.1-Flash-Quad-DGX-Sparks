# L9: no speculative decoding (determinism isolation)

Configuration: baseline + L1 (NCCL buffers) + `SPEC=none` (no `--speculative-config`, CUDA graph
capture sizes 1..8). Not a serving candidate: only here to find where temperature-0
divergence comes from.

| | DSpark, probabilistic draft | DSpark, greedy draft (L8) | no speculation (L9) |
|---|---|---|---|
| `greedy` gate, identical of 5 | 4/5, 3/5, 2/5, 2/5 | 1/5 | 1/5 |
| 10 identical requests, distinct texts | not measured (6 requests: 2) | 3 | 4 (5/3/1/1) |
| logprob range at char 92, " These" | -0.57 to -1.77 | -0.07 to -1.25 | -0.27 to -2.83 |
| logprob range at char 92, " Sh" | -0.27 to -1.89 | -0.48 to -2.82 | -0.08 to -2.10 |

(`logprobs-pos92-10runs.txt`.) Gates 10/10.

**Conclusion.** Temperature-0 outputs diverge just as much with no speculative decoding at
all: the divergence is in the target model's own forward pass, not in DSpark. This matches
AtomicChat's measurement of the same checkpoint on 4x B200 without speculation (4 % top-1
disagreement between runs) and their hypothesis of non-deterministic MoE kernels flipping
near-tied experts. Byte-exact temperature-0 reproducibility is not available on this stack
without a batch-invariant / deterministic kernel mode, which would cost speed; not pursued.

The gates keep measuring it (identical count) and fail only on garbled output.
