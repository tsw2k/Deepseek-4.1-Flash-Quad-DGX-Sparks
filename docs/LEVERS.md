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

Levers run at night now (`ops/night-levers.sh`, RUNBOOK "Night lever runs"): one queue line per
lever, read A/B/A against two same-night baselines. By hand, apply a lever by setting `LEVER_ENV`, `SPEC`, `DRAFT_SAMPLE` or another value in the operator's
`cluster.env`, then `scripts/fleet down dsv41`, `launch/cluster.sh ship`, `scripts/fleet up dsv41`
(mtxc-spark-cluster). The value then lives in every node's `cluster.env`, so a watchdog relaunch
keeps the same configuration. Give the run a label that names the lever, and restore the
baseline the same way.

| # | lever | change | why it might help | source | status |
|---|---|---|---|---|---|
| L0 | baseline | none (`PATCH_SET=measured`, K3, 600K) | reference point | 0xTank | **run** 2026-09-13 ([results](../results/2026-09-13-baseline-measured/NOTES.md)) |
| L1 | NCCL buffers | `LEVER_ENV="NCCL_BUFFSIZE=1048576 NCCL_LL128_BUFFSIZE=262144 NCCL_PROTO=^LL128 NCCL_MAX_NCHANNELS=8"` | MiaAI measured 4.7 GiB of pinned connection buffers per node, cut to 0.14 GiB. On a unified-memory box that is memory back for the head, and fewer reclaim stalls | MiaAI (SGLang, TP3) | **accepted** 2026-09-13: C1 +13 %, C6 +11 %, +10 GiB MemAvailable per node ([results](../results/2026-09-13-lever-L1-nccl-buffers/NOTES.md)) |
| L2 | Engram reads bypass the page cache | `PATCH_SET=measured-odirect` and `LEVER_ENV="DSV41_ENGRAM_ODIRECT=1"` (the patch is a no-op without the variable) | Rows are read through the page cache today, and on GB10 the cache competes with the engine for the same pool. Tech2Wild saw first runs after startup 30-60 % slower and suspected evicted Engram pages. MiaAI reads with `O_DIRECT` and no row cache ("~0% reuse") | MiaAI's idea; code written here, not copied (AGPL) | **rejected** 2026-09-13: on top of L1, prefill -8 % at 47K, C6 -6 %, no memory back ([results](../results/2026-09-13-lever-L2-odirect-on-L1/NOTES.md)) |
| L3 | K5 instead of K3 | `SPEC_K=5`, `MAXLEN=300000` | Tech2Wild's boot 10 shape; K3 was 0xTank's choice for 600K. Content-dependent: acceptance near 6 on code and counting, near 2 on prose | Tech2Wild | not run |
| L4 | b12x MXFP8 dense kernel | `LEVER_ENV="VLLM_DISABLED_KERNELS=FlashInferCutedslMxfp8LinearKernel,FlashInferCutlassMxfp8LinearKernel,MarlinMxfp8LinearKernel"` | MiaAI's profile: dense FP8 projections 52 ms on Triton, 50 on CUTLASS, 17 on b12x per step. bot-lab-21 accepted the same route in vLLM | MiaAI; bot-lab-21 | not run. `B12xMxfp8LinearKernel` and `VLLM_DISABLED_KERNELS` exist at `172d9a17`, but the kernel reports unsupported unless the `b12x` package is installed (`vllm[b12x]`). Check `python3 -c 'import b12x'` in the image; if missing this lever needs an image layer, and the boot log must show the b12x kernel selected |
| L5 | minimal patch set | `PATCH_SET=minimal` | keeps the tree's own changes to the indexer, `weight_utils` and `sparse_swa` instead of rolling them back | this repo | not run; gates decide |
| L6 | page-cache flusher on | `glm53-flusher.service` running during serving | the GLM stack needed it at load; during serving it evicts Engram pages every 60 s | mtxc GLM ops | not run; expect negative |
| L8 | greedy determinism | `DRAFT_SAMPLE=greedy launch/cluster.sh up` (speculative config `"draft_sample_method":"greedy"`) | First boot: 3/5 sequential temperature-0 runs byte-identical, the rest diverged on one near-tied token and stayed coherent. Probabilistic draft sampling varies acceptance, hence verify-batch sizes, hence kernels. Measure the `greedy` gate's identical count and acceptance length together | this cluster, 2026-09-13 | **rejected**: 1/5 identical, logits still move up to ~2.7 nats ([results](../results/2026-09-13-lever-L8-greedy-draft/NOTES.md)) |
| L9 | no speculative decoding (determinism isolation) | `SPEC=none` in cluster.env | After L8: is the temperature-0 divergence DSpark's or the target's? AtomicChat saw 4 % top-1 disagreement between runs without speculation on B200 | this cluster, 2026-09-13 | **done**: still 4 distinct texts in 10; the divergence is the target's, not DSpark's ([results](../results/2026-09-13-lever-L9-no-spec/NOTES.md)) |
| L7 | sysctls | `vm.min_free_kbytes=1048576`, `vm.watermark_scale_factor=200` | earlier reclaim on the unified pool | Tech2Wild | **rejected** 2026-09-17: C5 -22 %, C6 -20 % at equal GPU temperature and a cold cache, C1 and prefill unchanged. The reserve is paid for out of the Engram rows' page cache, which only matters once several streams share them ([results](../results/2026-09-17-L7-reverted-cold/NOTES.md)) |

## Rejected or out of scope for now

- **Adaptive speculative verification.** It pads speculative batches, and padded batches can
  hang SM120 sparse MLA (FlashInfer #5015, open).
- **A resident hot-row Engram cache.** bot-lab-21 measured a 20M-row resident set at 4-6 %
  slower single-stream.
- **`expandable_segments:False`.** MiaAI needed it on SGLang, where `True` produced NaN logits
  for prefills over 64 tokens. Both vLLM recipes run `True` and pass their checks. The
  `prefill` and `prefill_x4` gates test exactly that failure mode on every boot; if they ever
  fail, this becomes the first lever.
- **EXL3 3.5 bpw experts** (bot-lab-21 Pollard, deployment `dsv41x`). **Run 2026-09-14, not
  adopted.** +13-24 % throughput and 1.9x the KV pool, gates 10/10, 131K needle found, but the
  next-token distribution is far from the release: perplexity +19.5 % on English prose, top-1
  agreement 0.853 and mean KL 0.25 against a run-to-run noise floor of 0.988 and 0.0036. The
  release checkpoint on the same e47aa780 + tp3e stack sits inside that floor, so the gap is the
  quantization, not the stack ([results](../results/2026-09-14-exl3-3p5bpw/NOTES.md)).
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
- Switch: `DSV41_ENGRAM_ODIRECT=1`, default off. The patch lives in its own set,
  `patches/measured-odirect` (the `measured` set plus this change in `04-tony-mtxc-engram-odirect.diff`),
  so `measured` stays byte-identical to what 0xTank benchmarked. The boot log's
  `Engram DISK mode ... O_DIRECT True` line confirms it is active.

Measure: per-step time (`bench/tony` counting at C1), `Cached` in `/proc/meminfo` during a
30-minute mixed run, and the first-run-after-idle penalty (idle 15 minutes, then C1).
