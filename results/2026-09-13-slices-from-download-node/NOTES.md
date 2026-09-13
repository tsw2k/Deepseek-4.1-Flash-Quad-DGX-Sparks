# Engram slices from the download node

Validation of the download-once path next to the serving engine (baseline configuration,
`/health` 200 throughout, no watchdog probe failures, no change to the serving slices).

## Full shards, once, onto spark-01

`weights/fetch-engram.py /var/tmp/models/DeepSeek-V4.1-Flash-engram-full`, 189.2 GiB:

- First 72.7 GiB at `--mbps 80`, then restarted without a limit; the resume re-hashed the
  72.7 GiB already on disk and continued.
- Both shards: full sha256 equal to the LFS oids in `weights/manifest-dba1be0a.tsv`.
- spark-01 MemAvailable stayed at 4 GiB, Cached at 7 GiB, the same as the workers that were
  not downloading: the page-cache hygiene held.

Uplink, measured during this run: all four nodes leave through one public IP. With spark-01
downloading and three nodes pulling a test range at the same time, spark-01 fell from ~80 to
38 MB/s and the four summed to ~125 MB/s. The ceiling is shared (about 1 Gbit), so one
download node loses nothing against four parallel downloads. Unlimited, spark-01 ran at
~93 MB/s.

## `launch/cluster.sh slice --check` (38.5 min for all four ranks)

| rank | node | path | cut / pack | unpack (hashed twice) | result |
|---|---|---|---:|---:|---|
| 0 | spark-01 | cut in place from the full shards | 325 s | n/a | identical |
| 1 | spark-02 | pack, rail B rsyncd, unpack | 296 s | 230 s | identical |
| 2 | spark-03 | pack, rail B rsyncd, unpack | 274 s | 255 s | identical |
| 3 | spark-04 | pack, rail B rsyncd, unpack | 263 s | 281 s | identical |

"identical": rank, TP size, revision, row ranges and all 12 range digests equal to the
`engram-local.json` of the slice serving on that node, which was cut from Hugging Face range
requests in the first bring-up. Two independent paths produced the same bytes.

Scratch directories and packs were removed afterwards on every node; no sweeper was left
running. The serving slices were not replaced: they are byte-identical, so there is nothing
to replace.
