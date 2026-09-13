# Lever L2: O_DIRECT Engram row reads, on top of L1

Configuration: baseline + L1 + `PATCH_SET=measured-odirect` + `DSV41_ENGRAM_ODIRECT=1`. The boot
log showed `O_DIRECT True` for both Engram layers on all four ranks.

**Rejected.** Compared with L1, the configuration it stacks on:

| | L1 | L1 + L2 | change |
|---|---:|---:|---:|
| C1 aggregate / per-stream, tok/s | 46.1 / 50.7 | 45.0 / 49.5 | -2 % / -2 % |
| C2 / C3 / C4 aggregate | 73.1 / 95.8 / 112.8 | 71.2 / 94.2 / 111.0 | -2 to -3 % |
| C5 / C6 aggregate | 132.6 / 150.9 | 126.4 / 142.0 | -5 % / -6 % |
| cold prefill 2,950 / 11,592 / 46,810 / 93,335 tokens | 1,441 / 1,622 / 1,665 / 1,654 | 1,359 / 1,536 / 1,539 / 1,498 | -6 / -5 / **-8** / -9 % |
| needle 130K | pass, 80.1 s | pass, 88.6 s | |
| MemAvailable while serving (after the run) | 14-16 GiB | 10-12 GiB | no memory back |
| gates | 10/10 | 10/10 | |

Fails the acceptance rule on prefill (-8 % at 47K against a -5 % limit) and gains nothing on
decode.

Reading: the premise was that buffered Engram reads keep rows in the page cache and take memory
from the engine. With L1 in place the nodes already had ~10 GiB free, and O_DIRECT did not free
more, so the page cache was not what limited this stack. What O_DIRECT does add is cost per
row: two 4 KiB device reads (the weight and scale tables sit ~94 GiB apart), no read-ahead or
cache hits for repeated rows, and a slice copy in Python per row. That shows most in prefill,
which reads the most rows per step.

Possible follow-ups, not planned: interleave weight and scale per row in the slice format so a
row is one read (MiaAI's layout), or batch rows into io_uring submissions. Neither is worth it
while the page cache is not the constraint.

Serving reverted to L1 (`PATCH_SET=measured`).
