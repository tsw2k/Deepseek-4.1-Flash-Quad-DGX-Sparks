#!/usr/bin/env python3
"""Per-rank Engram slices: cut them from full shards, carry them as packs, check them.

  engram-slice.py cut MODEL_DIR --rank R --source FULL_DIR (--out DIR | --pack FILE) [--force]
  engram-slice.py unpack PACK --out DIR [--force]
  engram-slice.py compare DIR_A DIR_B

Each Engram shard (model-00047, model-00048) holds one layer's n-gram table (~94 GiB) plus
~150 MiB of ordinary Engram weights (wkv, q_weight, k_weight). A TP rank reads only its own
rows of the table, so a slice is a sparse copy of the shard at the original byte offsets:

  - the safetensors header, verbatim
  - rows [lo, hi) of layers.L.engram.embed.weight and .scale for this rank
  - every other tensor in the shard, in full (the regular loader reads those)
  - holes everywhere else (no disk)

plus engram-local.json with the row ranges, rank, TP size, revision and the sha256 of every
copied range. The patched engram.py (DSV41_ENGRAM_DIR) reads a slice only when its recorded
range covers the rank's rows; launch/node.sh refuses a slice made for another rank, because
a hole reads as zeros and degrades output without any error.

How slices move (docs/DESIGN.md, "Large files: download once"):

  cut --out     on the download node, from the full shards fetched once by fetch-engram.py,
                straight into a model directory (the download node's own rank)
  cut --pack    the same bytes as one plain file: a JSON header, then the ranges back to back
                (~47.5 GiB). A pack crosses rail B as an ordinary file. A sparse file would
                not: the sender reads its holes as zeros, 190 GiB per rank, and that lands in
                the page cache, which on GB10 is the GPU's memory.
  unpack        on the receiving node: rebuild the sparse shards from a pack, re-hash every
                range against the pack's digests, then write engram-local.json
  compare       two slices (e.g. a fresh cut and the one serving) must record the same rank,
                ranges, revision and digests

Row ranges are computed from config.json exactly as vLLM's EngramLayout does (prime-sized
hash heads, split by whole heads across ranks). For the pinned checkpoint at TP4 they match
the ranges published by Tech2Wild/Kai and 0xTank.

Every read and write drops its pages from the cache as it goes.
"""
import argparse
import base64
import hashlib
import json
import os
import struct
import sys
import time

PIN = "dba1be0a40aa45a94ad051997016db3960a90277"
CHUNK = 64 << 20
SYNC_EVERY = 1 << 30
PACK_MAGIC = b"DSV41EG1"
ENGRAM_SHARDS = ("model-00047-of-00048.safetensors", "model-00048-of-00048.safetensors")


def log(msg):
    print(msg, flush=True)


# ---- row ranges, as vllm/models/deepseek_v4_1/common/engram.py EngramLayout + ParallelEngramEmbedding
def is_prime(n):
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


def row_ranges(config_path, rank, tp):
    cfg = json.load(open(config_path))
    tc = cfg.get("text_config", cfg)
    seen, ranges = set(), {}
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
        per_rank = -(-len(heads) // tp)
        start = rank * per_rank
        ranges[layer] = (sum(heads[:start]), sum(heads[:start + per_rank]))
    return ranges


# ---- page-cache hygiene
def drop(fd, off=0, n=0):
    os.posix_fadvise(fd, off, n, os.POSIX_FADV_DONTNEED)


def copy_range(src_fd, src_off, dst_fd, dst_off, n, h):
    """Copy n bytes, hashing them; flush and drop pages every SYNC_EVERY bytes."""
    done, since = 0, 0
    while done < n:
        m = min(CHUNK, n - done)
        buf = os.pread(src_fd, m, src_off + done)
        if len(buf) != m:
            raise OSError(f"short read at {src_off + done}")
        h.update(buf)
        os.pwrite(dst_fd, buf, dst_off + done)
        drop(src_fd, src_off + done, m)
        done += m
        since += m
        if since >= SYNC_EVERY:
            os.fdatasync(dst_fd)
            drop(dst_fd)
            since = 0
    os.fdatasync(dst_fd)
    drop(dst_fd)


def verify_on_disk(fds, pieces):
    """Re-read every range from disk and compare with the digest taken while writing it."""
    for shard, off, n, label, want in pieces:
        fd, h = fds[shard], hashlib.sha256()
        for i in range(0, n, CHUNK):
            m = min(CHUNK, n - i)
            h.update(os.pread(fd, m, off + i))
            drop(fd, off + i, m)
        if h.hexdigest() != want:
            sys.exit(f"on-disk digest mismatch in {label}; partial files left in place")


def marker_guard(out_dir, rank, tp, revision, force):
    marker = os.path.join(out_dir, "engram-local.json")
    if os.path.exists(marker) and not force:
        have = json.load(open(marker))
        mine = (have.get("rank"), have.get("tp_size"), have.get("revision")) == (rank, tp, revision)
        sys.exit(f"{marker} already holds rank {have.get('rank')}/{have.get('tp_size')}"
                 f"{' (this rank)' if mine else ''}; --force to replace it")
    return marker


def write_marker(marker, ranges, rank, tp, revision, source, digests):
    tmp = marker + ".partial"
    json.dump({
        "layers": {str(k): list(v) for k, v in ranges.items()},
        "rank": rank,
        "tp_size": tp,
        "revision": revision,
        "source": source,
        "sha256": digests,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "sparse per-rank Engram slice; weights/engram-slice.py",
    }, open(tmp, "w"), indent=1)
    os.replace(tmp, marker)


# ---- cut
def plan_slice(model_dir, source_dir, ranges):
    """[(shard, offset, length, label)] and {shard: (size, header_bytes)} for this rank."""
    weight_map = json.load(open(os.path.join(model_dir, "model.safetensors.index.json")))["weight_map"]
    plan, shards = [], {}
    for layer, (lo, hi) in ranges.items():
        shard = weight_map[f"layers.{layer}.engram.embed.weight"]
        assert weight_map[f"layers.{layer}.engram.embed.scale"] == shard
        path = os.path.join(source_dir, shard)
        with open(path, "rb") as f:
            n = struct.unpack("<Q", f.read(8))[0]
            raw = struct.pack("<Q", n) + f.read(n)
        shards[shard] = (os.path.getsize(path), raw)
        for name, meta in json.loads(raw[8:]).items():
            if name == "__metadata__":
                continue
            a, b = meta["data_offsets"]
            if name in (f"layers.{layer}.engram.embed.weight", f"layers.{layer}.engram.embed.scale"):
                row = meta["shape"][1]  # fp8 / ue8m0: one byte per element
                assert b - a == meta["shape"][0] * row, name
                plan.append((shard, len(raw) + a + lo * row, (hi - lo) * row, f"{name}[{lo}:{hi}]"))
            else:
                assert name.startswith(f"layers.{layer}.engram."), f"unexpected tensor {name} in {shard}"
                plan.append((shard, len(raw) + a, b - a, name))
    return plan, shards


def verify_full_source(source_dir):
    """The full shards must carry the .sha256 stamp fetch-engram.py writes after a full check."""
    manifest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest-dba1be0a.tsv")
    want = {p: oid for p, _, oid in (l.rstrip("\n").split("\t") for l in open(manifest))}
    for shard in ENGRAM_SHARDS:
        stamp = os.path.join(source_dir, shard + ".sha256")
        if not os.path.exists(stamp) or open(stamp).read().split()[0] != want[shard]:
            sys.exit(f"{source_dir}/{shard} is not verified against the manifest (run weights/fetch-engram.py)")


def cmd_cut(a):
    if bool(a.out) == bool(a.pack):
        sys.exit("cut needs exactly one of --out DIR or --pack FILE")
    verify_full_source(a.source)
    ranges = row_ranges(os.path.join(a.model_dir, "config.json"), a.rank, a.tp)
    log("rows for rank %d/%d: %s" % (a.rank, a.tp, {k: list(v) for k, v in ranges.items()}))
    plan, shards = plan_slice(a.model_dir, a.source, ranges)
    total = sum(p[2] for p in plan)
    t0 = time.time()
    src_fds = {s: os.open(os.path.join(a.source, s), os.O_RDONLY) for s in shards}
    digests = {}

    if a.out:
        os.makedirs(a.out, exist_ok=True)
        marker = marker_guard(a.out, a.rank, a.tp, a.revision, a.force)
        log(f"cutting {total / 2**30:.1f} GiB into sparse shards in {a.out}")
        dst = {}
        for shard, (size, raw) in shards.items():
            fd = os.open(os.path.join(a.out, shard + ".partial"), os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o644)
            os.ftruncate(fd, size)
            os.pwrite(fd, raw, 0)
            dst[shard] = fd
        for shard, off, n, label in plan:
            h = hashlib.sha256()
            copy_range(src_fds[shard], off, dst[shard], off, n, h)
            digests[f"{shard}:{label}"] = h.hexdigest()
        verify_on_disk(dst, [(s, off, n, label, digests[f"{s}:{label}"]) for s, off, n, label in plan])
        for shard, fd in dst.items():
            if os.pread(fd, len(shards[shard][1]), 0) != shards[shard][1]:
                sys.exit(f"header mismatch in {shard}.partial")
            os.close(fd)
            os.replace(os.path.join(a.out, shard + ".partial"), os.path.join(a.out, shard))
        write_marker(marker, ranges, a.rank, a.tp, a.revision, f"cut:{os.path.abspath(a.source)}", digests)
        alloc = sum(os.stat(os.path.join(a.out, s)).st_blocks * 512 for s in shards)
        log(f"ok: {len(plan)} ranges, {alloc / 2**30:.1f} GiB allocated, {time.time() - t0:.0f}s; wrote {marker}")
        return

    # --pack: one pass. The header is written with placeholder digests of the final length,
    # the ranges are copied and hashed, then the header is rewritten in place (same length).
    def header(digest_of):
        meta = {
            "rank": a.rank, "tp_size": a.tp, "revision": a.revision,
            "layers": {str(k): list(v) for k, v in ranges.items()},
            "shards": {s: {"size": size, "header_b64": base64.b64encode(raw).decode()}
                       for s, (size, raw) in shards.items()},
            "pieces": [{"shard": s, "offset": off, "length": n, "label": label, "sha256": digest_of(s, label)}
                       for s, off, n, label in plan],
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
        }
        return json.dumps(meta).encode()

    placeholder = header(lambda s, label: "0" * 64)
    part = a.pack + ".partial"
    os.makedirs(os.path.dirname(os.path.abspath(a.pack)), exist_ok=True)
    log(f"packing {total / 2**30:.1f} GiB for rank {a.rank} into {a.pack}")
    pfd = os.open(part, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o644)
    os.pwrite(pfd, PACK_MAGIC + struct.pack("<Q", len(placeholder)) + placeholder, 0)
    pos, placed = 16 + len(placeholder), []
    for shard, off, n, label in plan:
        h = hashlib.sha256()
        copy_range(src_fds[shard], off, pfd, pos, n, h)
        digests[f"{shard}:{label}"] = h.hexdigest()
        placed.append((pos, n, label, h.hexdigest()))
        pos += n
    final = header(lambda s, label: digests[f"{s}:{label}"])
    assert len(final) == len(placeholder)
    os.pwrite(pfd, final, 16)
    verify_on_disk({"pack": pfd}, [("pack", p, n, label, want) for p, n, label, want in placed])
    os.fdatasync(pfd)
    os.close(pfd)
    os.replace(part, a.pack)
    log(f"ok: pack {pos / 2**30:.1f} GiB, {len(plan)} ranges, {time.time() - t0:.0f}s")


# ---- unpack
def cmd_unpack(a):
    t0 = time.time()
    pfd = os.open(a.pack, os.O_RDONLY)
    magic_len = os.pread(pfd, 16, 0)
    if magic_len[:8] != PACK_MAGIC:
        sys.exit(f"{a.pack} is not an Engram slice pack")
    hlen = struct.unpack("<Q", magic_len[8:])[0]
    meta = json.loads(os.pread(pfd, hlen, 16))
    rank, tp, revision = meta["rank"], meta["tp_size"], meta["revision"]
    os.makedirs(a.out, exist_ok=True)
    marker = marker_guard(a.out, rank, tp, revision, a.force)
    expect = 16 + hlen + sum(p["length"] for p in meta["pieces"])
    if os.fstat(pfd).st_size != expect:
        sys.exit(f"{a.pack} is {os.fstat(pfd).st_size} bytes, expected {expect}: incomplete transfer")
    log(f"unpacking rank {rank}/{tp} from {a.pack} into {a.out}")
    dst = {}
    for shard, s in meta["shards"].items():
        fd = os.open(os.path.join(a.out, shard + ".partial"), os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o644)
        os.ftruncate(fd, s["size"])
        os.pwrite(fd, base64.b64decode(s["header_b64"]), 0)
        dst[shard] = fd
    pos, digests = 16 + hlen, {}
    for p in meta["pieces"]:
        h = hashlib.sha256()
        copy_range(pfd, pos, dst[p["shard"]], p["offset"], p["length"], h)
        if h.hexdigest() != p["sha256"]:
            sys.exit(f"digest mismatch in {p['label']}: the pack is corrupt; partial files left in {a.out}")
        digests[f"{p['shard']}:{p['label']}"] = p["sha256"]
        pos += p["length"]
    # Re-read what landed on disk, not what was written: catches a write that did not stick.
    verify_on_disk(dst, [(p["shard"], p["offset"], p["length"], p["label"], p["sha256"]) for p in meta["pieces"]])
    for shard, fd in dst.items():
        raw = base64.b64decode(meta["shards"][shard]["header_b64"])
        if os.pread(fd, len(raw), 0) != raw:
            sys.exit(f"header mismatch in {shard}.partial")
        os.close(fd)
        os.replace(os.path.join(a.out, shard + ".partial"), os.path.join(a.out, shard))
    os.close(pfd)
    ranges = {int(k): tuple(v) for k, v in meta["layers"].items()}
    write_marker(marker, ranges, rank, tp, revision, f"pack:{os.path.basename(a.pack)}", digests)
    log(f"ok: {len(meta['pieces'])} ranges verified twice, {time.time() - t0:.0f}s; wrote {marker}")


# ---- compare
def cmd_compare(a):
    ja = json.load(open(os.path.join(a.dir_a, "engram-local.json")))
    jb = json.load(open(os.path.join(a.dir_b, "engram-local.json")))
    diffs = [k for k in ("rank", "tp_size", "revision", "layers", "sha256") if ja.get(k) != jb.get(k)]
    if diffs:
        for k in diffs:
            log(f"DIFFERENT {k}: {a.dir_a}={ja.get(k)!r:.200} {a.dir_b}={jb.get(k)!r:.200}")
        sys.exit(1)
    log(f"identical: rank {ja['rank']}/{ja['tp_size']}, {len(ja['sha256'])} range digests "
        f"({ja.get('source')} vs {jb.get('source')})")


ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
sub = ap.add_subparsers(dest="cmd", required=True)
c = sub.add_parser("cut")
c.add_argument("model_dir")
c.add_argument("--rank", type=int, required=True)
c.add_argument("--tp", type=int, default=4)
c.add_argument("--source", required=True, help="directory with the full, verified Engram shards")
c.add_argument("--out")
c.add_argument("--pack")
c.add_argument("--revision", default=PIN)
c.add_argument("--force", action="store_true")
u = sub.add_parser("unpack")
u.add_argument("pack")
u.add_argument("--out", required=True)
u.add_argument("--force", action="store_true")
m = sub.add_parser("compare")
m.add_argument("dir_a")
m.add_argument("dir_b")
args = ap.parse_args()
if args.cmd == "cut":
    assert 0 <= args.rank < args.tp
    cmd_cut(args)
elif args.cmd == "unpack":
    cmd_unpack(args)
else:
    cmd_compare(args)
