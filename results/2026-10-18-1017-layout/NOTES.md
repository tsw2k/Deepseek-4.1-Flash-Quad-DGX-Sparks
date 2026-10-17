# DeepSeek-V4.1-Flash-1017 laid out next to the serving release; uplink measured

2026-10-17 18:36 to 21:36 UTC (node clocks), all of it with the release serving. 1017 is not booted
yet; the A/B/A against the release is the next step.

## Layout (docs/RUNBOOK.md, "A new checkpoint next to the serving release")

| step | where | time |
|---|---|---|
| manifest of `deepseek-ai/DeepSeek-V4.1-Flash-1017` at 1bae0e10 (83 files, 48 shards new, 475.3 GiB) | HF tree API | |
| small files (config, tensor index, tokenizer, encoding, inference code) | spark-01 | 18:36 |
| full Engram shards 47/48, 189 GiB at 100 MB/s, sha256 against the LFS oid | spark-01 | 18:36-19:10 |
| every rank's slice (`CLUSTER_ENV=cluster.1017.env launch/cluster.sh slice`) | spark-01 cuts, packs over rail B | 19:45-20:25 (`slice-1017.log`) |
| full Engram shards deleted (no node holds them next to two model directories) | spark-01 | 20:26 |
| shards 1-8 on spark-01, then 9-46 split in four, each node downloading its quarter once | all four | 20:27-21:12 |
| every node pulls the other quarters from the owners' rsyncd over rail B, hashing each file | all four | 21:12-21:36 (`par-1017.log`) |

Row ranges per rank are the release's (same `config.json`). Every rank's `engram-local.json`
records rank 0-3, TP 4, revision 1bae0e10 and 12 hashed ranges; unpack verified each range twice.
`verify.py --size-only --manifest=weights/manifest-1017-1bae0e10.tsv`: 81/81 on every node, every
file hash-checked as it landed. Each node: 334 GiB for 1017, next to the release's 334 GiB; 85 GiB
free on spark-02/03/04.

## Uplink

Splitting the download over four nodes did not make it faster: 112 MB/s in total, as from one node.
A test against a second source (500 MB range requests to /dev/null):

| | Hetzner fsn1 | Hugging Face |
|---|---|---|
| one node | 104 MB/s | 103 MB/s |
| two nodes at once | 69 + 56 MB/s | |
| four nodes at once | two nodes refused (HTTP 429, per-IP limit), 73 + 56 MB/s | 56 + 52 + 30 + 27 MB/s |

One node fills its 1G port. Together the nodes get about 1 Gbit (the sums over-count a little:
the transfers end at different times), from Hetzner as from Hugging Face. The limit is on this
side and shared: the link from the nodes' switch to the router, the NAT or the firewall, not the
10G uplink and not Hugging Face. (speed.cloudflare.com answers 403 to non-browser clients.)

## Answer accuracy of the release, the reference for 1017

`bench/evalset.py` on the serving release (dba1be0a, measured set, L1, K5, 300K), concurrency 4,
16 min: `evalset-release-dba1be0a.json`.

| set | correct | accuracy | completion tokens, median / mean | truncated at 1024 |
|---|---|---|---|---|
| GSM8K (250) | 245 | 98.0 % | 144 / 160 | 1 |
| MMLU-Pro (280, 14 subjects) | 238 | 85.0 % | 89.5 / 183 | 9 |
