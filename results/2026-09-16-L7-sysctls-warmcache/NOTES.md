# Invalid for comparison: prefix cache from the previous run

Run taken without relaunching the engine after `2026-09-16-L7-pre`. `bench/tony/v41bench.py`
makes its tags unique within a run and identical across runs, so every prompt hit the prefix
cache left by L7-pre: prefill reads 8,122 to 194,485 tok/s and the 131K needle answers in 0.6 s
instead of 81 s. Decode numbers are depressed for the same reason (no real prefill work between
steps is not the issue; the comparison is simply not like-for-like). Kept as the record of the
trap. The like-for-like run is `2026-09-16-L7-sysctls`, taken after a relaunch.
