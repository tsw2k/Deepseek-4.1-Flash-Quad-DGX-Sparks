# DeepSeek-V4.1-Flash on four DGX Sparks

Serving [deepseek-ai/DeepSeek-V4.1-Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash)
(552B backbone MoE plus 196B of Engram tables, 8B/16B active, 1M context, vision, tools) with
DeepSeek's own weights, on four **ASUS Ascent GX10** (NVIDIA GB10, DGX Spark class) at
tensor-parallel 4, with vLLM, over a switched RoCEv2 fabric.

This is a self-contained recipe: pinned sources, patch sets as reviewable diffs, image build,
weight and Engram tooling, launcher, correctness gates and benchmark.

> **Status (2026-09-20): serving on the mtxc cluster as baseline + L1 + L3 (DSpark K5, 300K).** The measured configuration
> booted in 10 minutes, passed all gates and reproduced 0xTank's numbers within run-to-run spread
> ([baseline](results/2026-09-13-baseline-measured/NOTES.md)). NCCL buffer sizing (lever L1) then
> added +13 % single-stream and +11 % at six streams and gave ~10 GiB back per node
> ([L1](results/2026-09-13-lever-L1-nccl-buffers/NOTES.md)). O_DIRECT Engram reads (L2) and greedy
> drafting (L8) were measured and rejected ([levers](docs/LEVERS.md)). The EXL3 3.5 bpw checkpoint
> was brought up as a second deployment, measured against this one and not adopted: faster, but a
> different model at the next-token level ([EXL3](results/2026-09-14-exl3-3p5bpw/NOTES.md)).
> Numbers below labelled with an upstream source come from that group's hardware.

## The problem in one table

| | GiB |
|---|---:|
| checkpoint tensors | 475.2 |
| of which Engram n-gram tables | 189.1 |
| memory a GX10 shows the OS (host and GPU share it) | ~121.7 |
| weights per rank at TP4 with the Engram tables left on NVMe | 81.6 (Tech2Wild, measured) |

Stock vLLM keeps the Engram tables in host memory, which on GB10 is the GPU's memory, so the
release does not fit four Sparks. It fits once the tables stay on NVMe and each rank reads only
its own rows. Details: [docs/DESIGN.md](docs/DESIGN.md).

## What this reproduces

The path was worked out in public within two days of the release:

- **[Tech2Wild/Kai](https://github.com/tonyd2wild/DeepSeek-V4.1-Flash-vLLM-DGX-Spark)**:
  Engram on disk, CUDA graphs around a host-side lookup, the SM12x kernel and page fixes, boots
  1-10.
- **[0xTank](https://huggingface.co/0xTank/DeepSeek-V4.1-Flash-vLLM-4x-GB10-Recipe)**: the
  same patches on a later vLLM tree, plus a graph startup fix and a compact output-projection
  kernel, measured at 600K context with DSpark K3.

The default configuration here is 0xTank's measured tree, byte for byte
([docs/PROVENANCE.md](docs/PROVENANCE.md)). Only this cluster's fabric, storage and addresses
differ.

Reference numbers, ours next to theirs:

| | **this cluster, serving** (L1 + L3, K5 / 300K) | **this cluster**, baseline | 0xTank 600K / K3 | Tech2Wild boot 10, 300K / K5 |
|---|---|---|---|---|
| C1 aggregate / per-stream decode, tok/s | **48.7 / 54.6** | 40.5 / 44.7 | 39.5 / 43.4 | 38.0 / 43.1 |
| C6 aggregate, tok/s | **153.9** | 135.6 | 140.0 | 131.9 |
| cold prefill at 46,810 tokens, tok/s | **1,665** | 1,632 | 1,635 | 1,539 |
| needle, 131K | **pass, 80 s** | pass, 85 s | pass, 85 s | n/a |

Both runs use Tech2Wild's fixed prompt set (`bench/tony/`, vendored unchanged), so a run here
compares directly.

## Quality, not just gates

`bench/gates.py` proves the engine answers, counts, formats, sees images and survives long
prefills. It does not prove the distribution is the one the checkpoint defines: the EXL3 lane
passed all ten gates while changing one next-token argmax in seven.

`bench/quality.py` measures that distance directly. It scores fixed token windows of three corpora
(WikiText-2, Russian Wikipedia, this node's Python standard library) through `prompt_logprobs` and
compares two runs position by position: perplexity, top-1 agreement and a top-k KL bound.

| run against the release lane's own positions | top-1 agreement | KL mean |
|---|---|---|
| the same lane, a second time (the floor: nondeterministic MoE kernels) | 0.988 | 0.0036 |
| the release checkpoint on the EXL3 lane's stack (vLLM e47aa780 + tp3e) | 0.987 | 0.0036 |
| the EXL3 3.5 bpw checkpoint on that stack | 0.853 | 0.251 |

English prose; [reference](results/2026-09-14-quality-reference-release/NOTES.md) and
[EXL3](results/2026-09-14-exl3-3p5bpw/NOTES.md) have all three corpora. `quality.py probe REF_DIR`
is the short form for a boot check: ten windows per corpus, about a minute, non-zero exit if the
engine has moved.

## How it differs from upstream on this cluster

- **Large files come from the internet once.** Anything over 1 GB lands on one download node,
  is hash-verified there, and reaches the other nodes over rail B from its rsync daemon. In the
  first bring-up the 286 GiB checkpoint took 73 minutes over the shared datacenter uplink and
  about 6 minutes per node over rail B. Engram slices are cut on the download node from the
  full shards and shipped as packs over rail B
  ([docs/DESIGN.md](docs/DESIGN.md#large-files-download-once-fan-out-over-the-fabric)); the
  first bring-up still pulled them from Hugging Face per node.
- **No NFS.** Every node holds shards 1-46 and its own ~47.5 GiB sparse slice of the Engram
  shards.
- **Rail A carries NCCL only**, with the switch's PFC class (`NCCL_IB_TC=106`). The GID index is
  looked up per node at every launch, never pinned.
- **The patches are diffs**, not whole files, checked by hash at render time and again at
  launch. Diffing showed that the upstream whole-file copies also undo the pinned tree's own
  changes to three files (309 diff lines). The default set keeps that rollback because it is
  what was measured; a `minimal` set without it is a lever.
- **Guards** for failures that do not crash: the wrong rank's Engram slice, a stale recipe on
  one node, differing image IDs, the GLM watchdog still armed, a latched GPU clock.

## Path

```bash
cp cluster.env.example cluster.env
launch/cluster.sh ship                                    # git archive HEAD to every node
ssh spark-01 bash /home/mtxc/dsv41/build/build-image.sh   # in the maintenance window
bash build/ship-image.sh ./cluster.env
ssh spark-01 bash /home/mtxc/dsv41/weights/fetch.sh /home/mtxc/dsv41/cluster.env
bash weights/sync.sh ./cluster.env
launch/cluster.sh slice
launch/cluster.sh render
launch/cluster.sh up
bench/run.sh baseline-measured
```

Full sequence, including stopping GLM and rolling back: [docs/RUNBOOK.md](docs/RUNBOOK.md).

## Layout

| path | what |
|---|---|
| `patches/measured/`, `patches/minimal/` | diffs against vLLM `172d9a17`, with expected SHA-256 of the rendered files |
| `patches/exl3-tp3e/` | the EXL3 lane's files: names, hashes and the pinned commit they are fetched from |
| `patches/render.sh` | fetch pinned upstream files, apply a set, verify hashes |
| `build/` | image build (stable extension, overlay, FlashInfer runtime, runtime verification), image fan-out |
| `weights/` | download, manifest verification, rail B fan-out, per-rank Engram slices |
| `launch/node.sh` | one rank: preflight checks and the measured vLLM command line |
| `launch/cluster.sh` | ship, render, slice, preflight, up, down, status, Engram check |
| `cluster.env.example`, `cluster.exl3.env.example` | the release lane and the EXL3 lane as two deployments that take turns |
| `bench/gates.py` | correctness gates, run before any benchmark |
| `bench/run.sh` | configuration snapshot, gates, C1-C6 suite, needle; writes `results/` |
| `bench/quality.py` | corpora, next-token distance between two runs, and the boot probe |
| `bench/tony/` | Tech2Wild/Kai's benchmark, needle test and prompt set, unmodified |
| `ops/` | fleet watchdog and its systemd unit, hang check, GPU clock-latch burn |
| `docs/` | [design](docs/DESIGN.md), [provenance](docs/PROVENANCE.md), [runbook](docs/RUNBOOK.md), [levers](docs/LEVERS.md), [gotchas](docs/GOTCHAS.md) |

## Credits and license

DeepSeek-AI for the model. Tech2Wild/Kai and 0xTank for the recipe this reproduces. MiaAI-Lab
and bot-lab-21 for the measurements behind the levers. What came from whom is in
[NOTICE](NOTICE).

Apache-2.0 ([LICENSE](LICENSE)); vendored Tech2Wild files keep their MIT notice
([licenses/Tech2Wild-MIT.txt](licenses/Tech2Wild-MIT.txt)).
