# L7 rejected: the memory it holds back comes out of the Engram page cache

Two runs on 2026-09-17, both the first benchmark of their state, both after a relaunch (cold prefix
cache), both starting at 54-59 C on all four GPUs. The only difference is the two sysctls.

| C | L7 on (`2026-09-17-L7-cold-baseline`) | L7 off (this run) | ratio |
|---|---|---|---|
| C1 | 45.20 | 46.25 | 1.02 |
| C2 | 72.73 | 72.49 | 1.00 |
| C3 | 94.61 | 92.85 | 0.98 |
| C4 | 111.91 | 117.43 | 1.05 |
| C5 | 104.52 | 133.28 | **1.28** |
| C6 | 117.43 | 146.58 | **1.25** |

Aggregate tok/s over the eight categories. Cold prefill is unchanged (1,477 / 1,616 / 1,641 / 1,644
against 1,479 / 1,585 / 1,661 / 1,628 tok/s), and so is single-stream decode. DSpark mean acceptance
2.93 with the sysctls, 3.01 without.

## Why one stream does not see it

The reserve (1 GiB kept free, watermarks at 2 % of the zone) is real memory the kernel takes from the
page cache. On this cluster the page cache is mostly Engram rows read from NVMe. At one stream the
rows a step needs are read once and used once, so evicting them costs nothing measurable. At five or
six streams the same rows are hit by several sequences within a step window, and the reads that used
to come back from cache now go to the disk again. That is the 20-25 %.

## What was reverted

- `/etc/sysctl.d/99-dsv41.conf` renamed to `.disabled` on all four nodes; values back to the
  defaults 45155 / 10 (`sysctl -w`). The file is out of the repository.
- `launch/node.sh`'s boot floor back to MemAvailable >= 100 GiB.
- `docs/RUNBOOK.md` step 6 now says to leave the defaults alone, with the measurement behind it.

## The wrong turn, recorded

On 2026-09-16 the same comparison came out as "prefill flat, decode not measurable" and L7 was
adopted on memory grounds. Two of that day's three runs were spoiled (one by a warm prefix cache,
one by GPUs at 78-83 C), and the 27 % decode drop in the third was put down to heat. The heat was
real and so was the drop, but they were not the same thing: today's run reproduced the drop at 57 C.
A lever measured only through spoiled runs is not measured.
