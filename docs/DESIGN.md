# Design

## The model does not fit as shipped

`deepseek-ai/DeepSeek-V4.1-Flash` at `dba1be0a`: 48 shards, 475.2 GiB of tensors, 510.3 GB on
disk. Read from the safetensors headers, by component:

| component | GiB | dtype | where |
|---|---:|---|---|
| routed experts (40 layers x 384) | 268.9 | MXFP4 (I8-packed) | shards 1-46 |
| Engram n-gram tables (2 layers) | 189.1 | FP8 rows + UE8M0 scales | shards 47, 48 |
| DSpark / MTP draft layers | 7.4 | FP8 / BF16 | shards 1-46 |
| attention, norms, gates | 5.1 | FP8 | shards 1-46 |
| embedding + head | 2.5 | BF16 | shards 1-46 |
| shared experts | 1.3 | FP8 | shards 1-46 |
| vision encoder + aligner | 0.9 | BF16 | shards 1-46 |

A GX10 shows about 121.7 GiB to the OS, and that pool is both host RAM and GPU memory. Four of
them hold 487 GiB before the OS, the KV cache, CUDA graphs or NCCL take anything. Stock vLLM
keeps the Engram tables in host memory, which on GB10 is the same pool, so the shipped layout
needs about 119 GiB per rank for weights alone.

The Engram tables are the part that does not need to be in memory. A decode step touches 24
rows per Engram layer per token (3 n-gram sizes x 8 hash heads), 264 bytes each. With the
tables left on NVMe and rows read on demand (Tech2Wild/Kai's patch), a rank loads 81.6 GiB
including the draft layers and the vision encoder (measured upstream, boot 10). TP2 does not
fit either way; TP4 is the smallest layout for the release weights.

## Memory per rank

Upstream measurements on the same hardware, not ours yet:

| | Tech2Wild boot 10 (300K, K5) |
|---|---|
| weights, with draft layers and vision | 81.58 GiB |
| CUDA graphs | 1.99 GiB target + 0.55 GiB draft |
| KV pool at `--gpu-memory-utilization 0.80` | 5.15 GiB = 1,070,168 tokens |

KV is small because only four layers store global KV and the main KV is FP4 (890 bytes per
token for the whole model, per the model card). 0xTank's 600K/K3 configuration uses the same
budget. What bounds concurrency and context on this box is the headroom left for prefill
transients, not the KV pool.

## Disk per node

| | GiB |
|---|---:|
| shards 1-46 plus configs, tokenizer, encoding | 286.1 |
| this rank's Engram slice (sparse copy of shards 47-48) | ~47.5 |
| image | not measured yet; budget 50 |
| total | ~384 |

Free on 2026-09-13: 363 GiB on spark-01, 379 GiB on the others. Removing the unused
`Qwen3.8-Flash-Next-NVFP4` and `-fp8hybrid` trees (139 GiB per node) leaves ~500 GiB, enough for
V4.1 with GLM-5.3 still on disk for rollback.

### Engram slices

Each rank reads only its own hash heads: 6 of the 24 per layer. vLLM splits a table by whole
heads, and each head is a prime-sized bucket range, so the row boundaries are not multiples of
anything; `weights/engram-slice.py` recomputes them from `config.json` the way `EngramLayout`
does. For this checkpoint at TP4:

| rank | layer 1 rows | layer 14 rows |
|---|---|---|
| 0 | [0, 96000564) | [0, 96003054) |
| 1 | [96000564, 192001740) | [96003054, 192007016) |
| 2 | [192001740, 288003654) | [192007016, 288011564) |
| 3 | [288003654, 384006168) | [288011564, 384016682) |

These match the ranges Tech2Wild/Kai and 0xTank published.

The slice is a sparse file with the full shard's size: the header verbatim, this rank's rows
of `embed.weight` and `embed.scale` at their original offsets, the ~150 MiB of ordinary Engram
weights (`wkv`, `q_weight`, `k_weight`) in full because the regular loader reads them, and
holes everywhere else. It lives in the model directory under the shard's own name, so the
loader and the Engram reader see an ordinary checkpoint.

Upstream, workers kept a slice and fell back to the full shards over NFS when the slice did
not cover their rows. Here there is no full shard anywhere, so that fallback would read holes,
which are zeros: wrong output, no error. Two guards replace it. `engram-local.json` records
rank, TP size and revision, and `launch/node.sh` refuses a mismatch. After boot,
`cluster.sh engram` checks that every rank logged both tables as read node-local.

The slice comes straight from Hugging Face over range requests. No node ever downloads or
stores the 189 GiB of full Engram shards, and no slice crosses the fabric.

## Fabric use

| traffic | path |
|---|---|
| NCCL all-reduce, Gloo, vLLM rendezvous | rail A only (`rocep1s0f0`, 10.77.1.0/24), `NCCL_IB_TC=106` |
| checkpoint fan-out, image copy | rail B (rsyncd bound to 10.77.2.0/24) |
| Engram slices | Hugging Face, per node |
| API | head's rail A address, where LiteLLM already points; not the management network |

Upstream TP4 recipes run on one NCCL rail, and so does this cluster: a second NCCL rail was
measured slower here. Tech2Wild measured a decode step's 88 all-reduces at about 5 ms of a
63-70 ms step; MiaAI's SGLang profile puts the bulk of the rest in MoE and dense GEMMs, which
run at memory bandwidth.

## Why this path

Three published ways to run V4.1-Flash on four Sparks were compared on 2026-09-13:

| | vLLM + release weights | vLLM + EXL3 3.5 bpw experts | SGLang + release weights |
|---|---|---|---|
| source | Tech2Wild/Kai boot 10; 0xTank | Tech2Wild exl3tp4b; bot-lab-21 | MiaAI-Lab |
| booted at TP4 | yes, independently by three groups | yes | no, per its README ("validated for configuration only") |
| weights | DeepSeek's | third-party requantization, quality evidence thin | DeepSeek's |
| licence | MIT / Apache-2.0 | MIT | AGPL-3.0 |

This recipe takes the first path. It is the only TP4 layout with DeepSeek's own weights
that more than one group has booted. It stays close to 0xTank's measured tree, so its first
boot is a reproduction with a known answer, and every change after that is measured against
that answer (`docs/LEVERS.md`). The engineering ideas from the other two paths that do not
depend on their engines or their code are levers there. EXL3 can be a separate lane once the
release-weight baseline exists to evaluate it against.
