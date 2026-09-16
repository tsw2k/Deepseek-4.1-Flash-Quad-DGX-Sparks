# Gotchas

Failures reported by the upstream recipes and by this cluster's earlier GLM-5.3 and
Qwen3.8 bring-ups, arranged by symptom. The second column says where the fix lives in this
repo.

| symptom | cause | handled by |
|---|---|---|
| Engine boots cleanly, passes profiling and graph capture, then repeats one token; DSpark accepts nothing | patches mounted on the wrong vLLM tree (Tech2Wild: the `dsv41-feat` head after `99c83fbc4`) | pin `172d9a17`, rendered-hash check in `render.sh` and `node.sh`, `count`/`greedy`/`garble` gates |
| Output subtly wrong, no error | an Engram slice that does not cover the rank reads holes as zeros | `engram-local.json` rank check in `node.sh`; `cluster.sh engram` after boot |
| Ranks 1-3 read rank 0's Engram rows, silently | disk reader ignored the rank's row offset (Tech2Wild, found in audit) | fixed in the Engram patch; ranges recomputed in `engram-slice.py` |
| All four nodes wedge and the watchdogs reset them during boot | FlashInfer JIT compile at runtime with 22 jobs exhausted unified memory | kernels prebuilt in the image, `MAX_JOBS=2`, `verify-runtime.py` fails the build if anything would compile |
| `No common block size for 64` at KV init | vLLM picked the smallest listed block size; the V4 indexer refuses it | `--block-size 128` |
| DeepGEMM `block_kv == 32 or block_kv == 64` at decode warmup | ratio-1 indexer cache held 128 states per block | SM12x indexer pages of 64 states (patch 02) |
| A long request kills the engine in `persistent_topk` | it oversubscribes GB10's 48 SMs; its fallback needs more shared memory per block than GB10 has | `top_k_per_row_decode` (patch 07) |
| Requests stay "running" at 0.0 tok/s, process alive | padded speculative batch in SM120 sparse MLA (FlashInfer #5015) | exact capture sizes, adaptive verification off, `ops/hangcheck.sh` |
| New boot hangs at distributed init | a worker joined the old head's rendezvous on the same port | `cluster.sh up` refuses while any container exists; `down` stops the head first |
| NCCL all-gather dies on the first multi-node launch | `nofile` too low inside the container | `--ulimit nofile=1048576:1048576` |
| `NCCL error: unhandled system error` on one rank, or a silent hang at 96 % GPU and ~20 W | wrong or stale `NCCL_IB_GID_INDEX`; the RoCEv2 GID index differs between nodes and moves after reboots (this cluster, GLM-5.3) | GID looked up from sysfs for the rail A address at every launch |
| RoCE throughput quietly far below the link | traffic class does not match the switch's PFC priority | `NCCL_IB_TC=106` |
| Decode on all ranks set by one slow node; nothing in `nvidia-smi` | GB10 clock latch below 1 GHz; a reboot does not clear it | `ops/gpu-burn.sh` before launch; unplug the adapter 30-60 s |
| Decode speed swings 1.5x between identical runs | GB10 GPU fast/slow state (Tech2Wild issue #1), also after long idle | warm up before measuring; repeat borderline rows |
| First benchmark after startup 30-60 % slower on some prompt types | likely Engram pages evicted from the page cache (Tech2Wild, not proven) | lever L2 (O_DIRECT); keep the flusher off while serving |
| GLM comes back onto full GPUs minutes after it was stopped | `glm53-fleet.service` watchdog relaunches GLM after three failed health probes | runbook step 2; `node.sh` refuses while it is active |
| Anything slow or wedged during a big copy | page cache from downloads competing with the unified pool | downloads in the window only; `verify.py` and `engram-slice.py` drop pages as they go |
| Short tests pass, the first real request crashes | failure only in long decode after long prefill (this cluster, GLM-5.3) | `bench/tony/v41needle.py` at 131K and the C1-C6 suite before calling it serving |
| A worker rank dies; `/health` stays 200, nothing is logged, client requests hang with no reply | the head blocks in a collective waiting for the dead rank; the engine stops logging stats, so the hang check is blind (this cluster, failover test 2026-09-13) | watchdog checks every rank's container and sends a one-token canary |
| API reachable from the management network | vLLM has no auth | `API_HOST` is the head's rail A address; LiteLLM in front |

## Two benchmarks in a row do not compare

Two things drift within a day of benchmarking and both hit decode, not prefill:

- **The prefix cache.** `bench/tony/v41bench.py` makes each request's tag unique within a run and
  identical across runs, so a second run against the same live engine reads its prompts out of the
  first run's KV: prefill jumps to 8,000-194,000 tok/s and the 131K needle answers in 0.6 s instead
  of 81 s. Relaunch the engine between runs, or do not compare them.
- **Heat and acceptance.** After three runs the GB10s sat at 2,444-2,476 MHz of a 3,003 MHz maximum
  at 78-83 C, and DSpark mean acceptance had fallen from 3.22 to 2.89. Aggregate decode came out
  27 % below a run taken the same way two hours earlier. Prefill and the needle moved by 1-4 %.

A lever whose effect is smaller than that needs a cold cluster: one boot, one benchmark, nothing
benchmarked before it that day. `nvidia-smi --query-gpu=clocks.current.graphics,temperature.gpu`
before and after a run is the cheap check; `ops/gpu-burn.sh` is the thorough one.
