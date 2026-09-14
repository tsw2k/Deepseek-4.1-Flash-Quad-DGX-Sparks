# Quality reference: the release checkpoint, and its own run-to-run noise

2026-09-14 22:09–22:19 UTC, collected from the serving release lane (image `vllm-dsv41:172d9a17`,
patch set measured, L1 in LEVER_ENV, DSpark K3), at one request at a time next to production traffic.

`bench/quality.py collect`: 100 evenly spaced windows of 1024 tokens (BOS + 1023) per corpus, top-20
prompt logprobs for every position. Run `release-a` tokenized the corpora through the server; run
`release-b` scored the same token ids again (`--tokens-from release-a`). Corpora: `corpus-SHA256SUMS`
(the texts are not in this repository; `quality.py corpus` rebuilds them, and a rebuild whose hashes
differ is a different corpus). Per-position data stays on spark-01 in `/var/tmp/dsv41-quality`
(176 MB per run).

## Release against itself (`noise-release-a-b.json`)

| corpus | positions | ppl a | ppl b | ratio | top-1 agreement | KL mean | KL p90 | KL p99 |
|---|---|---|---|---|---|---|---|---|
| en-wiki | 102,300 | 2.931 | 2.930 | 1.000 | 0.988 | 0.0036 | 0.0070 | 0.0656 |
| ru-wiki | 102,300 | 2.459 | 2.459 | 1.000 | 0.989 | 0.0033 | 0.0055 | 0.0650 |
| code | 102,300 | 1.168 | 1.168 | 1.000 | 0.999 | 0.0003 | 0.0000 | 0.0023 |

The same model on the same tokens does not return the same distribution twice: about 1 % of
next-token argmaxes flip on prose, and the mean KL is 0.0035. This is the nondeterminism of the
MoE kernels already seen in greedy decoding (L9), now measured on the distribution. A quantized
checkpoint compared against `release-a` has to be read against this floor, not against zero.

The corpora are easy for this model (WikiText and the Python standard library are almost
certainly in its training data), so absolute perplexities are low and the code corpus in
particular separates little; top-1 agreement and KL on the two prose corpora carry the comparison.
