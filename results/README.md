# Results

One directory per recorded run, written by `bench/run.sh`: `<UTC date>-<label>/` with the
configuration snapshot (`run.txt`, `cluster.env`, `docker inspect` per rank, rendered patch
hashes, host state), `gates.json`, the benchmark output and the needle result.

A run without passing gates is not recorded. Add a `NOTES.md` for anything the snapshot does
not capture (flusher state, sysctls, what else was running, anything odd).

Empty until the first boot on this cluster.
