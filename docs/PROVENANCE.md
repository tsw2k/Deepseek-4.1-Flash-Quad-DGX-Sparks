# Provenance

Every input is pinned by commit or content hash. A change to any row below is a new
configuration and needs a new baseline.

## Pins

| input | pin |
|---|---|
| checkpoint | `deepseek-ai/DeepSeek-V4.1-Flash` @ `dba1be0a40aa45a94ad051997016db3960a90277` (88 files, 510,313,353,565 bytes; hashes in `weights/manifest-dba1be0a.tsv`) |
| vLLM source | `vllm-project/vllm` @ `172d9a17117219952fd3d4cdbb04ecb2a09163f4` (force-pushed `dsv41-feat` lineage, 2026-09-11 02:50 UTC; not on main, no branch points at it) |
| base image | `vllm/vllm-openai:nightly-8a728663c1c3eeace834a95f5654fa653cc1998c` (tag; `build-image.sh` logs the digest it pulled) |
| FlashInfer | `07869c61ba581e6d6b8ad8d142f4a6c89b707cc1` (0.7.0rc1) |
| FlashInfer 3rdparty | CUTLASS `b46b16d0`, CCCL `16bd510c`, spdlog `c3aed4b6` |
| stable-extension CUTLASS | tag `v4.7.1` |
| Tech2Wild/Kai recipe | `tonyd2wild/DeepSeek-V4.1-Flash-vLLM-DGX-Spark` @ `fc725ecf10` (patch files; bench files) |
| 0xTank recipe | `0xTank/DeepSeek-V4.1-Flash-vLLM-4x-GB10-Recipe` @ `7afa210d12` |

The checkpoint's later commits after the weight upload touch only README and `encoding/`. The
last one, `dba1be0a`, fixes tool namespaces in the reference prompt encoder, so it is the pin
here. MiaAI-Lab pins `fb2764a5`, from before that fix; 0xTank pins `dba1be0a` through an
identical mirror. This recipe downloads from `deepseek-ai` directly.

## Which vLLM tree

Tech2Wild's patches were written against `e47aa780b`, a commit on the day-0 `dsv41-feat` branch.
That branch was force-pushed, merged into main (#56214) and deleted on 2026-09-11. Tech2Wild
reports that the same patches on a later **branch head** boot without error and emit one
repeated garbage token, and names `99c83fbc4` ("Separate DeepSeek V4 and V4.1 indexer block
sizes") as the change underneath.

0xTank built `172d9a17` with the same seven patch files, byte for byte, plus four of their own.
They ran Tech2Wild's full benchmark on it and passed a 131K needle test, and they published
every prompt and response.

Checked here through the GitHub API on 2026-09-13:
- `172d9a17` is a commit of the rewritten `dsv41-feat` history, not of main. It shares merge
  base `07b75534` with main and has 4 commits main does not.
- `99c83fbc4`, the commit Tech2Wild blames, has exactly one parent, and that parent is
  `172d9a17`. 0xTank's pin is therefore the last commit of the rewritten branch **before**
  that change. Both upstream reports agree: the tree just before it works, the tree just after
  it emits garbage. Moving the pin forward by one commit is the move that broke upstream.
- `172d9a17` is 291 commits ahead of `e47aa780b` and 1 behind it.
- `e47aa780b` is still reachable through branch `dsv41-optimized`. `172d9a17` is reachable by
  full sha only, and GitHub can garbage-collect unreferenced commits, so `build-image.sh`
  keeps a tarball of the checked-out tree next to the image.
- All ten patched files exist at `172d9a17`; `compact_o_proj.py` is a new file.

So `172d9a17` is the pin, with `e47aa780b` as the documented fallback if the first boot
disagrees. Do not bump it without re-deriving the patches and passing the gates.

## Patch sets

Upstream ships these patches as whole-file replacements. Diffed against the pinned tree, each
file turns out to carry a small functional change. Three files also carry a silent
**rollback**: the tree had changed them between `e47aa780b` and `172d9a17`, and a whole-file
copy puts the old lines back.

| file | functional change (vs `e47aa780b`) | changed by `172d9a17` | whole-file copy on `172d9a17` |
|---|---|---|---|
| `v1/attention/backends/mla/sparse_swa.py` | +7 | 6 lines | reverts them |
| `models/deepseek_v4_1/attention.py` | +33 -3 | none | same as diff |
| `models/deepseek_v4_1/nvidia/flashinfer_sparse.py` | +36 -1 | none | same as diff |
| `models/deepseek_v4_1/common/engram.py` | +380 -2 | none | same as diff |
| `model_executor/model_loader/weight_utils.py` | +6 | 81 lines | reverts them |
| `models/deepseek_v4_1/nvidia/model_state.py` | +27 | none | same as diff |
| `model_executor/layers/sparse_attn_indexer.py` | +7 -4 | 222 lines | reverts them |
| `v1/worker/gpu_worker.py` (0xTank) | +25 vs `172d9a17` | n/a | n/a |
| `models/deepseek_v4/nvidia/ops/o_proj.py` (0xTank) | +7 -1 | n/a | n/a |
| `model_executor/kernels/linear/mxfp8/emulation.py` (0xTank) | +10 | n/a | n/a |
| `models/deepseek_v4/nvidia/ops/compact_o_proj.py` (0xTank) | new file | n/a | n/a |

In the indexer and `sparse_swa.py`, the reverted lines come from #56228 (DeepSeek-V4.1 model
definitions) and #55355 (DeepSeek-V4 CPU backend), not from `99c83fbc4`.

Two sets are kept, both as diffs against `172d9a17`:

- **`patches/measured`** reproduces the tree 0xTank benchmarked, rollbacks included. Each diff
  applied to the pinned file gives a result byte-identical to their released file; the
  expected hashes are in `patches/measured/SHA256SUMS` and equal 0xTank's published
  `SHA256SUMS`. This is the default and the baseline.
- **`patches/minimal`** holds the functional changes only, rebased cleanly onto `172d9a17`, so
  the tree's own changes to those three files stay. Nobody has booted it. It is lever L5.

`patches/render.sh` fetches the pinned upstream files, checks them against
`patches/UPSTREAM-SHA256SUMS`, applies a set and checks the result before a node can mount it.

## What has been verified, and where

Done off-cluster, as text processing only (no build, no GPU):
- both sets round-trip: diff applied to the pinned file equals the intended file, byte for byte
- the vendored patch and bench files match 0xTank's published hashes (`prompts-v1.json` differs
  from 0xTank's copy by one trailing newline; this repo carries Tech2Wild's original)
- Engram row ranges recomputed from `config.json` match both upstream tables
- the Engram shards' layout (`embed` tables at offset 0, `wkv`/`q`/`k` weights at the tail)
  was read from the pinned shards' headers over HTTP

Not yet done anywhere on this cluster: build, boot, gates, benchmark. `results/` is empty
until then, and nothing in this repository is a measurement of ours.
