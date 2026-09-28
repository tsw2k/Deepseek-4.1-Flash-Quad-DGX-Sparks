# NVFP4 again, under the memory guard (2026-09-28): the guard held, the checkpoint does not fit

Second attempt at `nvidia/DeepSeek-V4.1-Flash-NVFP4` (3431dde3, experts only) on the release stack,
started by hand at 15:12 UTC, with `ops/memguard.sh` in enforce mode at a 6 GiB floor on every rank.

## What happened (UTC)

| time | event |
|---|---|
| 15:12 | runner started; the first baseline run's results directory already existed from the morning's observe run, so `bench/run.sh` refused to overwrite it and the runner logged it as a gate failure (it was not: that baseline had passed 10/10 at 14:05). Fixed: every runner start now writes to its own directory |
| 15:19 | relaunch with the NVFP4 model directory |
| 15:20:16 | weight loading starts on every rank (`Available RAM: 35.7 GiB`) |
| ~15:21 | MemAvailable on the three workers falls at about 1 GiB a second from ~30 GiB, with MemFree flat at 0.7-1 GiB: memory that is neither free nor reclaimable page cache |
| 15:22:03 | guard trips on spark-04 at 6,059 MiB (t+166 s), 15:22:08 spark-02 at 6,117 MiB, 15:22:11 spark-03 at 5,871 MiB; each kills its rank by PID |
| 15:22 | every node back to 116-117 GiB within seconds; `cluster.sh up` reports the failed boot with the three trip lines; the head's rank (lowest 14 GiB) is stopped by the runner |
| 15:37 | baseline serving again: gates 10/10, quality probe on the floor; watchdog re-armed |

`memguard-nvfp4-spark-0N.log` has each rank's curve. The alert went out through `ops/notify.sh` and
was logged as not sent, because Telegram is not configured yet.

## What it settles

- **The guard works as designed.** The same boot that hung three nodes for 53 hours on 09-26 ended
  as a failed boot with no node affected. Total unavailability for the whole run: three relaunches.
- **The NVFP4 checkpoint does not load within a GB10's memory on this stack.** The workers would
  have needed well over their ~30 GiB of headroom at the point of the drop. The head, with the
  API server and a lighter share, bottomed at 14 GiB when the workers were killed.
- **Where the memory goes is still open.** It is not page cache (MemFree stays near 1 GiB while
  MemAvailable falls); it is GPU allocations or process memory growing faster than the weights
  themselves could (7.28 GiB per expert shard, read at a few hundred MB/s). The two candidates stay
  as before: FlashInfer's CUTLASS NVFP4 MoE weight processing holding a second copy of each layer,
  and the multimodal wrapper keeping every loaded tensor alive until the last one. The next step is
  a sampler of per-process anonymous memory and GPU memory during the load, not another boot.
