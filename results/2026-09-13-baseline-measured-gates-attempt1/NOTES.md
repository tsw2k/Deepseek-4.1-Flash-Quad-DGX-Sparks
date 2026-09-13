# First gates run on the measured configuration

9/10 gates passed. `greedy` (then: two sequential temperature-0 requests must be
byte-identical) failed.

Follow-up on the same boot: 5 sequential runs of the greedy prompt gave 3 byte-identical
outputs; the other 2 diverged at char 93 on a near-tied token ("These molecules scatter"
vs "Shorter blue wavelengths scatter") and stayed coherent and correct. Counting 1..60 was
identical 3/3.

Decision (user, 2026-09-13): record greedy determinism as a measurement, run the baseline,
and test `draft_sample_method: greedy` as lever L8.

Flusher stopped on all nodes; sysctls untouched (vm.min_free_kbytes 45155,
watermark_scale_factor 10).
