# L7: vm.min_free_kbytes and vm.watermark_scale_factor

2026-09-16, release lane serving (measured set, K3, 600K, L1). Three runs on the same day:

| run | sysctls | prefix cache | GPU state |
|---|---|---|---|
| `2026-09-16-L7-pre` | defaults: min_free 45,155 kB, watermark_scale_factor 10 | cold | ~2 h after boot |
| `2026-09-16-L7-sysctls-warmcache` | min_free 1,048,576 kB, wsf 200 | **warm, invalid** | |
| `2026-09-16-L7-sysctls` | same | cold (relaunched) | after two benchmark runs |
| `2026-09-16-L7-sysctls-repeat` | same | cold (relaunched) | after three benchmark runs |

## What the sysctls did to memory

MemFree per node went from 1.1-5.4 GiB to 6.6-8.7 GiB: the kernel now keeps hard free memory
instead of page cache. MemAvailable reads ~10 GiB lower because the reserve is subtracted from it.
The engine kept answering throughout (health 200, a chat request in 0.34 s).

## What it did to throughput: nothing measurable, and the decode comparison is confounded

| | pre | after (run 1) | after (run 2) |
|---|---|---|---|
| prefill 2,950 / 11,592 / 46,810 / 93,335 tok/s | 1,520 / 1,676 / 1,691 / 1,643 | 1,456 / 1,625 / 1,664 / 1,623 | 1,462 / 1,645 / 1,680 / 1,617 |
| needle 131K, TTFT s | 81.4 | 81.9 | 82.9 |
| DSpark mean acceptance | 3.22 | 2.96 | 2.89 |

Prefill and the needle are flat within 1-4 %. Decode is not comparable across these runs: by the
third benchmark of the day the GPUs sat at 2,444-2,476 MHz of a 3,003 MHz maximum at 78-83 C, and
DSpark acceptance had fallen from 3.22 to 2.89. Both cut decode throughput directly, and the second
run's aggregate came out 27 % below the first while the first matched the pre-change run. One batch
in run 1 (C4 narrative) queued 60 s behind other work; it did not repeat.

**Status: kept, on memory grounds, not throughput.** The change is applied at runtime only
(`sysctl -w`), so a reboot restores the defaults. What it buys is 6-8 GiB of hard free memory per
node, the resource whose absence produces the GB10 allocator stalls this recipe keeps running into;
what it costs is not visible in prefill or the needle. A clean decode number needs a cold cluster:
one boot, one benchmark, no benchmarks before it that day.
