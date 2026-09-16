# Gates and the quality probe on the restored release lane, 2026-09-16

The run that wired `quality.py probe` into `bench/run.sh`. Gates 10/10; the probe scored ten
windows per corpus against `release-a` and stayed on the floor: top-1 0.989/0.990/0.999,
KL 0.0033/0.0026/0.0002. 32 s for the probe.
