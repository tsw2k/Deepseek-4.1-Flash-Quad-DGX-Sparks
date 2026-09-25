# Night of 2026-09-24: L6 (page-cache flusher during serving) rejected

A/B/A, 02:00-02:51 Europe/Istanbul. The lever is `glm53-flusher.service` on all four nodes while the
engine serves: `sync; echo 3 > /proc/sys/vm/drop_caches` every 60 s. The runner started it once the
lever was serving (02:24) and stopped it after its benchmark (02:33); all three runs passed the
gates and the quality probe (en-wiki top-1 0.990).

| run | C1 | C3 | C5 | C6 | C1 per-stream | prefill 2,950 / 46,810 / 93,335 | needle 131K, s | acceptance |
|---|---|---|---|---|---|---|---|---|
| 01 A baseline | 49.5 | 97.4 | 134.4 | 151.6 | 55.5 | 1,517 / 1,675 / 1,651 | 80.5 | 3.58 |
| 02 **L6** flusher | 49.3 | 94.0 | 130.3 | **142.4** | 55.7 | 1,525 / **1,587** / **1,566** | **83.2** | 3.66 |
| 03 A baseline | 48.3 | 97.6 | 141.7 | 151.2 | 53.8 | 1,504 / 1,678 / 1,643 | 80.6 | 3.64 |

Against the mean of its baselines: C6 -5.9 %, C5 -5.6 %, C3 -3.6 %, cold prefill at 46,810 tokens
-5.4 % and at 93,335 -4.9 %, the 131K needle 3.3 % slower; single-stream decode and short prefill
unchanged. Rejected, as expected.

It is the same mechanism as L7, from the other side: the page cache on this cluster is mostly Engram
rows, dropping it every minute sends reads that several streams, or a long prefill, would have shared
back to NVMe. The flusher belongs to weight loading only (the GLM stack needed it there); it must not
run while the engine serves.
