#!/usr/bin/env python3
"""Cut this rank's slice of the two Engram shards into the local model directory.

usage: engram-slice.py MODEL_DIR --rank R [--tp 4] [--source hf|/path/to/full/model]
                       [--revision SHA] [--mbps 800] [--force]

Each Engram shard (model-00047, model-00048) holds one layer's n-gram table (~94 GiB) plus
~150 MiB of ordinary Engram weights (wkv, q_weight, k_weight). A TP rank reads only its own
rows of the table, so the file this writes is a sparse copy at the original byte offsets:

  - the safetensors header, verbatim
  - rows [lo, hi) of layers.L.engram.embed.weight and .scale for this rank
  - every other tensor in the shard, in full (the regular loader reads those)
  - holes everywhere else (no disk)

and then engram-local.json with the row ranges, rank, TP size and revision. The patched
engram.py (DSV41_ENGRAM_DIR) reads the copy only when the recorded range covers the rank's
rows. On this cluster there is no full shard to fall back to, so launch/node.sh also refuses
to start a rank whose engram-local.json names a different rank: a hole reads as zeros, which
degrades output without any error.

Row ranges are computed here from config.json exactly as vLLM's EngramLayout does (prime-sized
hash heads, split by whole heads across ranks), not copied from a table. For the pinned
checkpoint at TP4 they match the ranges published by Tech2Wild/Kai and 0xTank.

With --source hf the bytes come straight from Hugging Face over HTTP range requests at the
pinned revision; each range is fetched twice at sampled offsets to catch transport errors,
and the tail tensors are compared byte for byte against a second fetch. With a local path
the source must be a full, manifest-verified copy.

Writes are rate-limited and dropped from the page cache as they go: on GB10 the page cache is
the GPU's memory.
"""
import argparse
import hashlib
import json
import os
import random
import struct
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO = "deepseek-ai/DeepSeek-V4.1-Flash"
PIN = "dba1be0a40aa45a94ad051997016db3960a90277"
CHUNK = 64 << 20

ap = argparse.ArgumentParser()
ap.add_argument("model_dir")
ap.add_argument("--rank", type=int, required=True)
ap.add_argument("--tp", type=int, default=4)
ap.add_argument("--source", default="hf")
ap.add_argument("--revision", default=PIN)
ap.add_argument("--mbps", type=float, default=800.0)
ap.add_argument("--jobs", type=int, default=8)
ap.add_argument("--force", action="store_true")
args = ap.parse_args()
assert 0 <= args.rank < args.tp

md = args.model_dir
marker = os.path.join(md, "engram-local.json")
if os.path.exists(marker) and not args.force:
    have = json.load(open(marker))
    if (have.get("rank"), have.get("tp_size"), have.get("revision")) == (args.rank, args.tp, args.revision):
        print(f"{marker} already holds rank {args.rank}/{args.tp} at {args.revision[:10]}; --force to redo")
        sys.exit(0)
    sys.exit(f"{marker} holds rank {have.get('rank')}/{have.get('tp_size')}; refusing to overwrite without --force")


# ---- row ranges, as vllm/models/deepseek_v4_1/common/engram.py EngramLayout + ParallelEngramEmbedding
def is_prime(n: int) -> bool:
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for a in (2, 7, 61):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


cfg = json.load(open(os.path.join(md, "config.json")))
tc = cfg.get("text_config", cfg)
seen: set[int] = set()
ranges = {}
for layer, table_rows in zip(tc["engram_layer_ids"], tc["engram_num_embeddings"]):
    heads = []
    for _ in range(tc["engram_max_ngram_size"] - 1):
        cur = tc["engram_vocab_size"] - 1
        for _ in range(tc["engram_n_heads"]):
            cur += 1
            while not is_prime(cur) or cur in seen:
                cur += 1
            seen.add(cur)
            heads.append(cur)
    assert sum(heads) <= table_rows, (layer, sum(heads), table_rows)
    per_rank = -(-len(heads) // args.tp)
    start = args.rank * per_rank
    lo, hi = sum(heads[:start]), sum(heads[:start + per_rank])
    ranges[layer] = (lo, hi)
print("rows for rank %d/%d: %s" % (args.rank, args.tp, {k: list(v) for k, v in ranges.items()}), flush=True)

# ---- source access
if args.source == "hf":
    base = f"https://huggingface.co/{REPO}/resolve/{args.revision}/"

    def fetch(shard: str, off: int, n: int) -> bytes:
        for attempt in range(8):
            try:
                req = urllib.request.Request(base + shard, headers={"Range": f"bytes={off}-{off + n - 1}"})
                with urllib.request.urlopen(req, timeout=300) as r:
                    if r.status != 206:
                        raise OSError(f"HTTP {r.status} for a range request")
                    buf = r.read()
                if len(buf) != n:
                    raise OSError(f"short range {len(buf)} != {n}")
                return buf
            except Exception as e:  # noqa: BLE001
                if attempt == 7:
                    raise
                print(f"  retry {shard}@{off}: {e}", flush=True)
                time.sleep(2 ** attempt)
        raise AssertionError

    def shard_size(shard: str) -> int:
        manifest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest-dba1be0a.tsv")
        for line in open(manifest):
            p, size, _ = line.split("\t")
            if p == shard:
                return int(size)
        raise KeyError(shard)
else:
    src_dir = args.source

    def fetch(shard: str, off: int, n: int) -> bytes:
        fd = os.open(os.path.join(src_dir, shard), os.O_RDONLY)
        try:
            buf = os.pread(fd, n, off)
            os.posix_fadvise(fd, off, n, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)
        if len(buf) != n:
            raise OSError(f"short read {shard}@{off}")
        return buf

    def shard_size(shard: str) -> int:
        return os.path.getsize(os.path.join(src_dir, shard))

if args.revision != PIN and args.source == "hf":
    sys.exit(f"manifest sizes are for {PIN}; refusing revision {args.revision}")

weight_map = json.load(open(os.path.join(md, "model.safetensors.index.json")))["weight_map"]
t0 = time.time()
plan = []  # (shard, abs_offset, length, row_bytes or 0 for a whole tensor, label)
shards = {}
for layer, (lo, hi) in ranges.items():
    shard = weight_map[f"layers.{layer}.engram.embed.weight"]
    assert weight_map[f"layers.{layer}.engram.embed.scale"] == shard
    if shard not in shards:
        n = struct.unpack("<Q", fetch(shard, 0, 8))[0]
        raw = fetch(shard, 0, 8 + n)
        hdr = json.loads(raw[8:])
        shards[shard] = {"size": shard_size(shard), "header": raw, "tensors": hdr}
    s = shards[shard]
    hlen = len(s["header"])
    for name, meta in s["tensors"].items():
        if name == "__metadata__":
            continue
        a, b = meta["data_offsets"]
        if name in (f"layers.{layer}.engram.embed.weight", f"layers.{layer}.engram.embed.scale"):
            row = meta["shape"][1]  # fp8 / ue8m0: one byte per element
            assert (b - a) == meta["shape"][0] * row, name
            plan.append((shard, hlen + a + lo * row, (hi - lo) * row, row, f"{name}[{lo}:{hi}]"))
        else:
            assert name.startswith(f"layers.{layer}.engram."), f"unexpected tensor {name} in {shard}"
            plan.append((shard, hlen + a, b - a, 0, name))

total = sum(p[2] for p in plan)
print(f"copying {total / 2**30:.1f} GiB into {len(shards)} sparse shards from {args.source}", flush=True)

fds = {}
for shard, s in shards.items():
    part = os.path.join(md, shard + ".partial")
    fd = os.open(part, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o644)
    os.ftruncate(fd, s["size"])
    os.pwrite(fd, s["header"], 0)
    fds[shard] = fd

lock = threading.Lock()
progress = {"sent": 0, "synced": 0}
started = time.time()


def copy_piece(job):
    shard, off, n = job
    # Throttle before reading: every worker reserves its bytes against the shared rate.
    with lock:
        progress["sent"] += n
        wait = progress["sent"] / (args.mbps * 1e6) - (time.time() - started)
    if wait > 0:
        time.sleep(wait)
    buf = fetch(shard, off, n)
    fd = fds[shard]
    os.pwrite(fd, buf, off)
    return n


pieces = [(shard, off + i, min(CHUNK, n - i)) for shard, off, n, _, _ in plan for i in range(0, n, CHUNK)]
done = 0
with ThreadPoolExecutor(max_workers=args.jobs) as ex:
    for n in ex.map(copy_piece, pieces):
        done += n
        if done - progress["synced"] >= 2 << 30:
            # DONTNEED only drops clean pages: flush first, or the cache keeps growing.
            for fd in fds.values():
                os.fdatasync(fd)
                os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
            progress["synced"] = done
            el = time.time() - started
            print(f"  {done / 2**30:6.1f} / {total / 2**30:.1f} GiB  {done / el / 1e6:5.0f} MB/s", flush=True)
for fd in fds.values():
    os.fdatasync(fd)
    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)

# ---- verify: header, sampled rows against an independent read, tail tensors in full
rng = random.Random(args.rank)
checks = []  # (shard, abs_offset, length, label)
for shard in shards:
    checks.append((shard, 0, len(shards[shard]["header"]), f"{shard} header"))
for shard, off, n, row, label in plan:
    if row:
        rows = n // row
        for r in sorted({0, rows - 1} | {rng.randrange(rows) for _ in range(300)}):
            checks.append((shard, off + r * row, row, f"{label} local row {r}"))
    else:
        checks.append((shard, off, n, label))


def check(c):
    shard, off, n, label = c
    return None if os.pread(fds[shard], n, off) == fetch(shard, off, n) else label


bad = 0
with ThreadPoolExecutor(max_workers=args.jobs) as ex:
    for label in ex.map(check, checks):
        if label:
            bad += 1
            print(f"MISMATCH {label}")
checked = len(checks)

digests = {}
for shard, off, n, _, label in plan:
    fd = fds[shard]
    h = hashlib.sha256()
    for i in range(0, n, CHUNK):
        m = min(CHUNK, n - i)
        h.update(os.pread(fd, m, off + i))
        os.posix_fadvise(fd, off + i, m, os.POSIX_FADV_DONTNEED)
    digests[f"{shard}:{label}"] = h.hexdigest()

if bad:
    sys.exit(f"verify failed: {bad} mismatches in {checked} checks; partial files left for inspection")

for shard, fd in fds.items():
    os.close(fd)
    os.replace(os.path.join(md, shard + ".partial"), os.path.join(md, shard))
tmp = marker + ".partial"
json.dump({
    "layers": {str(k): list(v) for k, v in ranges.items()},
    "rank": args.rank,
    "tp_size": args.tp,
    "revision": args.revision,
    "source": args.source,
    "sha256": digests,
    "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "note": "sparse per-rank Engram slice; weights/engram-slice.py",
}, open(tmp, "w"), indent=1)
os.replace(tmp, marker)
alloc = sum(os.stat(os.path.join(md, s)).st_blocks * 512 for s in shards)
print(f"ok: {checked} checks, {alloc / 2**30:.1f} GiB allocated on disk, {time.time() - t0:.0f}s; wrote {marker}")
