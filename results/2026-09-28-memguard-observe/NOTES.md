# A healthy release boot under the memory guard, observe mode (2026-09-28)

`@baseline` run started by hand at 13:59 UTC: one relaunch of the serving configuration (release,
K5, 300K, L1) and one full `bench/run.sh`, with `ops/memguard.sh` in observe mode on every rank.
Gates 10/10, quality probe on the floor, serving after 5 minutes. `memguard-*.log` has each rank's
memory curve (one line per GiB of new low); `baseline/` is the benchmark.

| rank | lowest MemAvailable, boot and benchmark | when | lowest MemFree |
|---|---|---|---|
| 0 spark-01 (head) | 11,224 MiB | t+681 s, during the benchmark | 969 MiB during weight load |
| 1 spark-02 | 13,299 MiB | t+680 s | 3,202 MiB |
| 2 spark-03 | 13,077 MiB | t+693 s | 972 MiB during weight load |
| 3 spark-04 | 13,175 MiB | t+702 s | 2,283 MiB |

What it settles:
- **MemFree cannot be the trigger.** A healthy weight load drives it to about 1 GiB (the page cache
  holds what was just read) and the boot is fine.
- **MemAvailable can.** Its lowest point in a healthy run is 11.2 GiB on the head, reached in the
  benchmark, not the load; the workers stay above 13 GiB.
- **Floor 6 GiB, enforce, on every rank.** 5 GiB of margin under the healthiest-case low and 6 GiB
  left for the kill to act before the pool is gone. A false trip costs one watchdog relaunch and an
  alert; a missed one cost 53 hours.
