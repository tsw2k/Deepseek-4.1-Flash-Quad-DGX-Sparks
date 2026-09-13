# Runbook: first boot on the mtxc cluster

From four GX10s serving GLM-5.3-Flash to V4.1-Flash serving, gated and benchmarked, with a way
back at every step. Commands run on the operator host unless a step says otherwise.
`cluster.env` is `cluster.env.example` copied and checked.

Steps 0-1 do not disturb GLM. Step 2 opens the maintenance window: the API is down from there
until step 9, or until the rollback.

## 0. Before the window (GLM keeps serving)

- [ ] Recipe committed; `launch/cluster.sh ship` puts `git archive HEAD` and `cluster.env` on
      every node (no working-directory debris).
- [ ] `hf` CLI on spark-01: `python3 -m pip install --user -U huggingface_hub`.
- [ ] Decide the window length. Nothing below has been timed on these nodes. Upstream: image
      build tens of minutes to hours at `MAX_JOBS` 2-4; boot 11-13 minutes once cached.

## 1. Disk (GLM keeps serving)

On every node, confirm nothing uses the Qwen trees, then remove them (139 GiB per node):

```bash
docker ps -a --format '{{.Names}} {{.Mounts}}' | grep -i qwen    # must print nothing
sudo rm -rf /var/tmp/models/Qwen3.8-Flash-Next-NVFP4 /var/tmp/models/Qwen3.8-Flash-Next-NVFP4-fp8hybrid
docker image prune                                                 # dangling layers only
df -h /                                                            # expect ~500 GiB free
```

GLM-5.3 weights and its image stay: they are the rollback.

## 2. Open the window: stop GLM without letting it come back

On spark-01 the fleet watchdog relaunches GLM when `/health` fails, and it would fight the new
engine for the GPUs and port 8000. Stop it first, then GLM:

```bash
ssh spark-01 sudo systemctl stop glm53-fleet.service
for n in spark-01 spark-02 spark-03 spark-04; do ssh $n 'docker stop vllm_glm53'; done   # head first
```

Leave `glm53-flusher.service` running through steps 3-5: the downloads and the image build
fill the page cache. Stop it before step 6 (it would keep dropping Engram pages while serving)
and record that it is off:

```bash
for n in spark-01 spark-02 spark-03 spark-04; do ssh $n sudo systemctl stop glm53-flusher.service; done
```

`launch/node.sh` refuses to start while `glm53-fleet.service` is active or any other model
container runs.

## 3. Image (spark-01, then fan out)

```bash
ssh spark-01 "bash /home/mtxc/dsv41/build/build-image.sh"
bash build/ship-image.sh ./cluster.env        # rail B; checks all four image IDs match
```

The build refuses to run next to a loaded model and logs the lowest MemAvailable it saw.

Check each GPU's clock before relying on it (needs the GPU free):

```bash
for n in spark-01 spark-02 spark-03 spark-04; do ssh $n "bash /home/mtxc/dsv41/ops/gpu-burn.sh"; done
```

Below 60 TFLOPS or under ~1 GHz under load means the clock latch. Fix it before going on: shut
down, unplug the adapter for 30-60 s, power on. A reboot does not clear it.

## 4. Weights

```bash
ssh spark-01 "bash /home/mtxc/dsv41/weights/fetch.sh /home/mtxc/dsv41/cluster.env"   # 286 GiB + verify
bash weights/sync.sh ./cluster.env                                                      # rail B + verify on each node
launch/cluster.sh slice                                                                 # ~47.5 GiB per node, from HF ranges
```

`slice` computes each rank's rows, writes the sparse Engram shards into the model directory,
checks sampled rows and the tail tensors against a second fetch, then writes
`engram-local.json`. A node without that file has no slice.

## 5. Patches

```bash
launch/cluster.sh render      # measured set; each node verifies the rendered hashes
```

## 6. Host settings for serving

- [ ] `glm53-flusher.service` stopped on all nodes (step 2).
- [ ] Optional, and it changes the host, so record it: Tech2Wild recommends
      `vm.min_free_kbytes=1048576` and `vm.watermark_scale_factor=200` so the kernel reclaims
      earlier on the unified pool. The nodes run 45155 / 10 today. Upstream measured with them
      set, so apply them for the baseline if the goal is a like-for-like comparison, and note
      it in the result.

`nofile` does not need a host change: the launcher sets 1048576 on the container.

## 7. Boot

```bash
launch/cluster.sh preflight   # every check on every rank, nothing started
launch/cluster.sh up          # 3, 2, 1, then 0; waits for /health; then the Engram check
```

While it loads, high GPU utilisation at low power (~20-25 W) with no log progress is a hung
collective, not work (GID or fabric; see `docs/GOTCHAS.md`). If a rank exits, `up` prints its
log tail. Clean up with `launch/cluster.sh down`, which saves every rank's log.

## 8. Gates, then the baseline

```bash
bench/run.sh baseline-measured --gates-only
bench/run.sh baseline-measured
```

No gate failure is waived. The benchmark reproduces 0xTank's run, prompt for prompt. Their
numbers are the reference, not a target (`README.md`).

Add a short `results/<date>-baseline-measured/NOTES.md`: flusher state, sysctls, anything
unusual. Commit the result directory.

## 9. Put it behind LiteLLM, or roll back

**Keep V4.1:** add a `deepseek-v4.1-flash` entry to the LiteLLM config in mtxc-spark-cluster
(`api_base` is the same `VLLM_BASE`, `http://10.77.1.11:8000/v1`), reload the proxy, and point
a watchdog at the new engine before closing the window. `glm53-fleet.service` stays disabled
while V4.1 serves:

```bash
ssh spark-01 sudo systemctl disable glm53-fleet.service
```

**Roll back to GLM:**

```bash
launch/cluster.sh down
for n in spark-01 spark-02 spark-03 spark-04; do ssh $n sudo systemctl start glm53-flusher.service; done
ssh spark-01 sudo systemctl start glm53-fleet.service
```

The watchdog probes `http://127.0.0.1:8000/health` every 60 s. After three failures it removes
the `vllm_glm53` containers, drops caches and relaunches GLM worker-first, so expect ~3 minutes
before recovery starts and a full GLM load after that. Nothing GLM needs was deleted, so the
rollback is a relaunch, not a download.

The same watchdog is why step 2 stops it first. Left running next to V4.1, it cannot see
V4.1's health (different container, rail A address), and within three minutes it would
launch GLM onto GPUs that are already full.
