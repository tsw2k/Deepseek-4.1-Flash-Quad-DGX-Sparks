# Failover test: one worker killed

Serving the baseline configuration, no traffic except the probes below.

| UTC | event |
|---|---|
| 18:00:10 | `docker kill vllm_dsv41` on spark-03 (rank 2) |
| 18:00:22 | rank 2 `Exited (137)`; head still `/health` 200, nothing in its log |
| 18:01:12 | a client-style request to the head: no reply within 120 s; `/health` still 200; no engine stats logged, so the hang check sees nothing |
| 18:04:28 | watchdog v1 (probing `/health` and the hang check) has not noticed after 4 minutes; restarted with v2 (per-rank container check + one-token canary) |
| 18:04:29 | v2 first probe: `rank 2 on spark-03: exited` (1/3) |
| 18:06:2x | head container exits by itself (NCCL timeout on the stuck request) |
| 18:06:30 | 3/3: recovery starts (`cluster.sh down`, logs in `/var/tmp/dsv41-logs/20260913T180631Z/`) |
| 18:13:54 | `RECOVERY OK`: boot 6 min (warm kernel caches), every rank reads its Engram rows node-local |

After recovery: 10/10 gates (`gates.json`), a request through LiteLLM with a client key
answered correctly.

Findings:
- A dead worker is invisible to `/health` on this vLLM multi-node executor. With v1 the head
  would have exited on its own after ~6 minutes and `/health` would then have failed, so
  recovery would still have happened, but only after the first client request hit the dead
  rank and every request in between hung.
- With v2 from the start: detection in 1 probe, recovery after 3 (~2 min), boot ~6-10 min.
- `greedy` 2/5 identical here (4/5 and 3/5 on the first boot): the determinism measurement
  varies run to run; L8 stays the lever to test.
