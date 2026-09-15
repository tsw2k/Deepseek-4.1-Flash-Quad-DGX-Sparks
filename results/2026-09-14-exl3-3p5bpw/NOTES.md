# EXL3 3.5 bpw lane (dsv41x) against the release lane

2026-09-14, deployment `dsv41x`: bot-lab-21's DeepSeek-V4.1-Flash-EXL3-3.5bpw-Pollard at f129e31a,
image `vllm-dsv41:exl3-e47aa780` (vLLM e47aa780b + `_C_stable_libtorch` sm_121a + FlashInfer
0.7.0rc1 07869c61 prebuilt + cuda-exl3 6a1ffc34), patch set exl3-tp3e (Tech2Wild fc725ecf). The
serving shape is the release lane's: 600K, DSpark K3 probabilistic, gmu 0.80, L1 NCCL buffers.
Release lane numbers are `2026-09-13-lever-L1-nccl-buffers` (same shape, vLLM 172d9a17 + measured).

Two things differ from the release lane at once, the checkpoint and the vLLM stack under it; the
control at the end separates them.

## Memory and context

| | release lane | EXL3 lane |
|---|---|---|
| model memory, ranks 0 and 3 | 81.92 GiB | 56.61 GiB |
| model memory, ranks 1 and 2 | 81.92 GiB | 68.93 GiB (the 640-wide expert slices) |
| KV pool | 1,737,422 tokens (2.90 x 600K) | 3,372,154 tokens (5.62 x 600K) |
| MemAvailable after sizing | | 27-29 GiB narrow ranks, 17 GiB wide ranks |
| boot to /health | | 10 min |

vLLM sizes KV from rank 0, a narrow rank; the wide ranks kept 17 GiB free, so this held.

## Speed and correctness (`bench-exl3-3p5bpw.md`, `gates.json`, `needle-131k.json`)

| C | release aggregate tok/s | EXL3 aggregate tok/s | ratio |
|---|---|---|---|
| C1 | 46.13 | 52.27 | 1.13 |
| C2 | 73.13 | 87.37 | 1.19 |
| C3 | 95.81 | 115.2 | 1.20 |
| C4 | 112.8 | 140.07 | 1.24 |
| C5 | 132.55 | 160.7 | 1.21 |
| C6 | 150.95 | 180.33 | 1.19 |

Gates 10/10 (identity, count, greedy, garble, prefill, prefill x4, json, tool, vision, thinking).
Needle at 130,258 prompt tokens found; prefill 1,461 tok/s against the release lane's 1,627 (-10 %).
DSpark mean acceptance length 3.14 against 3.09.

## Next-token distribution (`release-a-vs-exl3-a.json`, `bench/quality.py`)

Same 307K token positions as `2026-09-14-quality-reference-release`, scored by the EXL3 lane.

| corpus | ppl release | ppl EXL3 | ratio | top-1 agreement | KL mean | KL p90 | KL p99 | release noise: top-1 / KL |
|---|---|---|---|---|---|---|---|---|
| en-wiki | 2.931 | 3.502 | 1.195 | 0.853 | 0.251 | 0.686 | 3.155 | 0.988 / 0.0036 |
| ru-wiki | 2.459 | 2.756 | 1.121 | 0.887 | 0.169 | 0.430 | 2.519 | 0.989 / 0.0033 |
| code | 1.168 | 1.210 | 1.036 | 0.977 | 0.050 | 0.016 | 1.348 | 0.999 / 0.0003 |

Against `release-b` the figures agree to the third decimal, so this is not the reference run's
noise. The gap is 50-170 times the release lane's run-to-run KL and it is spread evenly: per-window
mean KL on en-wiki runs from 0.13 to 0.42 (p10 0.18, p90 0.34), KL is of the same size at every
position band from 1 to 1023, and 3.3 % of the tokens the release model gives p > 0.9 change their
argmax (25 % of those at p 0.5-0.9). A broken Engram lookup or a long-context fault would
concentrate somewhere; this does not. Every rank read its own Engram rows node-local.

The gates passing says the model is coherent, follows formats and retrieves at 131K. It does not say
the distribution is close: perplexity is 19.5 % higher on English prose.

## Control: the release checkpoint on the EXL3 lane's stack (2026-09-15)

The comparison above changes the checkpoint and the stack together (vLLM e47aa780 + tp3e against
172d9a17 + measured). The control boots `dsv41x` with the release MODEL_DIR (same image, patch set,
serving shape; only MODEL_DIR differs) and scores the same positions.

| corpus | release lane vs control: top-1 / KL mean (`release-a-vs-ctl.json`) | control vs EXL3: ppl ratio / top-1 / KL mean (`ctl-vs-exl3-a.json`) |
|---|---|---|
| en-wiki | 0.987 / 0.0036 | 1.196 / 0.853 / 0.251 |
| ru-wiki | 0.989 / 0.0035 | 1.121 / 0.887 / 0.168 |
| code | 0.999 / 0.0003 | 1.036 / 0.977 / 0.050 |

The two stacks are indistinguishable on the release checkpoint (the control sits exactly on the
release lane's run-to-run floor), and the EXL3 checkpoint on that same stack reproduces the whole
gap. **The distance is the quantization.** On this stack the release checkpoint gets a KV pool of
878,188 tokens against the measured set's 1,737,422 (0xTank's graph-memory changes are not in tp3e).

## Verdict

Not adopted. The EXL3 lane is faster and holds twice the context, and it passes every functional
gate, but on English prose it is a different model at the next-token level (one argmax in seven
changes, perplexity +19.5 %). The release lane stays in production. The lane stays reproducible
(`cluster.exl3.env.example`, deployment `dsv41x`); its EXL3 directories remain on spark-03/04 only.
