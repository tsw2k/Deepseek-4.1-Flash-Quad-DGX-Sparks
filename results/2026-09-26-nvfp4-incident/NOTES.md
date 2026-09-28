# 2026-09-26: the NVFP4 boot hung three nodes; production down 53 hours

## What happened (UTC)

| time | event |
|---|---|
| 09-26 08:16 | A/B/A run for `nvidia/DeepSeek-V4.1-Flash-NVFP4` started by hand in the daytime (`ops/night-levers.sh`, deadline overridden). Baseline run: gates 10/10, probe on the floor |
| 08:36 | relaunch with the NVFP4 model directory; vLLM selects the `FLASHINFER_CUTLASS` NVFP4 MoE backend on all ranks |
| 08:37:45 | weight loading starts (`Checkpoint size: 491.08 GiB. Available RAM: 34.85 GiB`) |
| ~08:45 | spark-02, spark-03 and spark-04 stop responding: ping answers, sshd does not send its banner, the engine log advances by one line every few minutes. spark-01 (head) stays usable |
| 09:01 | runner: `NVFP4-nvidia did not boot` (spark-02's container gone) |
| 09:29 | runner cannot read GPU temperatures on the hung nodes, gives up waiting, starts the restore: the baseline cannot boot without three ranks; watchdog left paused |
| 09-28 13:27 | all four nodes power-cycled by remote hands |
| 13:30 | LiteLLM had not come back after the power cut (container restarted without its network, `Can't reach database server at db`); recreated with `docker compose up -d --force-recreate litellm` |
| 13:36 | release lane serving again (`fleet up dsv41`): gates 10/10, quality probe on the floor, LiteLLM healthy, public endpoint 200 |

Outage of the API: 08:36 on 09-26 to 13:36 on 09-28, 53 hours. Most of it was waiting for the power
cycle: the operator's alert went out at 09:45 and did not reach anyone.

## Why

Not fully established. What the logs show: the hang began inside weight loading, before KV sizing
and graph capture, on the three worker ranks; no container was OOM-killed (`OOMKilled: false`), and the
kernel logged repeated `NVRM ... Out of memory` on the head. On GB10 the GPU allocates from the same
pool as the host, and when that pool runs out the kernel cannot reclaim GPU memory, so userland
starves while the kernel keeps answering ping: the failure Tech2Wild recorded on their TP3 bring-up.

What is different from the release checkpoint that boots in five minutes: the routed experts are
NVFP4 (7.28 GiB per shard against 6.88), with an extra global and input scale per projection
(46,080 more tensors), processed by FlashInfer's CUTLASS NVFP4 MoE path at load time. Candidates:
a transient second copy of each layer's experts during that processing, and the multimodal wrapper
keeping every mapped tensor alive until the last one is loaded (Tech2Wild's streaming `vl_model.py`
fix, which the measured patch set does not carry). Neither is confirmed.

## What was missing

1. **A memory guard during boot.** `launch/node.sh` checks MemAvailable once, before `docker run`.
   Nothing watched memory while the weights loaded; Tech2Wild's `memguard.sh` stops all ranks before
   any node crosses a floor, which turns this into a clean failed boot. This is the fix.
2. **A load test before the fleet.** A new checkpoint format went straight to a four-rank boot on
   production nodes. With a guard it would still have been a failed boot, not an outage.
3. **Out-of-band power.** There is no BMC or switched PDU in reach, so a hung node needs a person.
4. **An alert that reaches someone.** The push notification was the only signal.
5. **LiteLLM after a power cut.** `restart: unless-stopped` brought the container back without its
   network; the stack needs a check after an unclean shutdown.

NVFP4 is off the queue and stays off until the guard exists and the load has been understood.
