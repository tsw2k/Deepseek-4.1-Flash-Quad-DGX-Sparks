# Levers

The baseline is the measured configuration, booted unchanged (`docs/RUNBOOK.md`). Every lever
after that is one change, booted, gated and benchmarked against the baseline with
`bench/run.sh`. A lever that fails a gate is rejected whatever its speed.

**Accept** a lever when all three hold:
- C1 per-stream decode or C6 aggregate improves by 5 % or more
- cold prefill at 46,810 tokens loses no more than 5 %
- all gates pass

Accepted levers stack in the order below. The rule is 0xTank's and bot-lab-21's ladder, made a
little stricter: upstream measured ±5 % run to run on a single config, and the GB10 GPU slow
state (Tech2Wild issue #1) can move one cell by up to 1.5x. Repeat any borderline row before
deciding.

Apply a lever with `LEVER_ENV` / `VLLM_EXTRA` or a `cluster.env` value, and give the run a
label that names it.

| # | lever | change | why it might help | source | status |
|---|---|---|---|---|---|
| L0 | baseline | none (`PATCH_SET=measured`, K3, 600K) | reference point | 0xTank | not run |
| L1 | NCCL buffers | `LEVER_ENV="NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8"` | MiaAI measured 4.7 GiB of pinned connection buffers per node, cut to 0.14 GiB. On a unified-memory box that is memory back for the head, and fewer reclaim stalls | MiaAI (SGLang, TP3) | not run |
| L2 | Engram reads bypass the page cache | new patch: `DiskEngramTable` reads with `O_DIRECT` into aligned per-thread buffers | Rows are read through the page cache today, and on GB10 the cache competes with the engine for the same pool. Tech2Wild saw first runs after startup 30-60 % slower and suspected evicted Engram pages. MiaAI reads with `O_DIRECT` and no row cache ("~0% reuse") | MiaAI's idea; code to be written here, not copied (AGPL) | design below |
| L3 | K5 instead of K3 | `SPEC_K=5`, `MAXLEN=300000` | Tech2Wild's boot 10 shape; K3 was 0xTank's choice for 600K. Content-dependent: acceptance near 6 on code and counting, near 2 on prose | Tech2Wild | not run |
| L4 | b12x MXFP8 dense kernel | `LEVER_ENV="VLLM_DISABLED_KERNELS=FlashInferCutedslMxfp8LinearKernel,FlashInferCutlassMxfp8LinearKernel,MarlinMxfp8LinearKernel"` | MiaAI's profile: dense FP8 projections 52 ms on Triton, 50 on CUTLASS, 17 on b12x per step. bot-lab-21 accepted the same route in vLLM | MiaAI; bot-lab-21 | not run. `B12xMxfp8LinearKernel` and `VLLM_DISABLED_KERNELS` exist at `172d9a17`, but the kernel reports unsupported unless the `b12x` package is installed (`vllm[b12x]`). Check `python3 -c 'import b12x'` in the image; if missing this lever needs an image layer, and the boot log must show the b12x kernel selected |
| L5 | minimal patch set | `PATCH_SET=minimal` | keeps the tree's own changes to the indexer, `weight_utils` and `sparse_swa` instead of rolling them back | this repo | not run; gates decide |
| L6 | page-cache flusher on | `glm53-flusher.service` running during serving | the GLM stack needed it at load; during serving it evicts Engram pages every 60 s | mtxc GLM ops | not run; expect negative |
| L7 | sysctls | `vm.min_free_kbytes=1048576`, `vm.watermark_scale_factor=200` | earlier reclaim on the unified pool | Tech2Wild | not run |

## Rejected or out of scope for now

- **Adaptive speculative verification.** It pads speculative batches, and padded batches can
  hang SM120 sparse MLA (FlashInfer #5015, open).
- **A resident hot-row Engram cache.** bot-lab-21 measured a 20M-row resident set at 4-6 %
  slower single-stream.
- **`expandable_segments:False`.** MiaAI needed it on SGLang, where `True` produced NaN logits
  for prefills over 64 tokens. Both vLLM recipes run `True` and pass their checks. The
  `prefill` and `prefill_x4` gates test exactly that failure mode on every boot; if they ever
  fail, this becomes the first lever.
- **EXL3 3.5 bpw experts.** Triple the KV pool, faster decode, third-party weights with thin
  quality evidence. A separate lane once L0 exists to evaluate it against, with a quality eval
  run on both.
- **Dual-rail NCCL.** Measured slower on this cluster for other models; not revisited here.

## L2 design: O_DIRECT Engram reads

A 4 KiB O_DIRECT read per row, as in MiaAI's row store, but against the release shard layout
rather than a repacked file:

- Open each shard twice: the existing fd for headers, and `O_RDONLY | O_DIRECT` for rows.
- Each pool thread owns a 4 KiB buffer from `mmap` (page-aligned, as `O_DIRECT` needs).
- A row at byte offset `o` of length `n` (256 for weights, 8 for scales) is read as the 4 KiB
  block at `o & ~4095`, then sliced. Rows that cross a block edge read two blocks.
- The weight and the scale of a row live about 94 GiB apart (tables, not interleaved), so a
  row costs two reads instead of MiaAI's one. A decode token touches 24 rows per Engram layer,
  of which a rank owns 6: 12 rows over both layers, 24 reads. At 8 sequences with a K3 verify
  window that is up to ~770 reads per step before de-duplication. MiaAI measured ~112k IOPS at
  queue depth 64 on their Spark's NVMe; ours is not measured, so measure it first
  (`fio --direct=1 --rw=randread --bs=4k --iodepth=64`).
- Keep the thread pool and the staging before the forward; only `_kai_pread_rows` changes.
- Switch: `DSV41_ENGRAM_ODIRECT=1`, default off, so L0 is untouched.

Measure: per-step time (`bench/tony` counting at C1), `Cached` in `/proc/meminfo` during a
30-minute mixed run, and the first-run-after-idle penalty (idle 15 minutes, then C1).
