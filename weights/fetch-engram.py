#!/usr/bin/env python3
"""Download the two full Engram shards once, onto the download node, and verify them.

usage: fetch-engram.py CACHE_DIR [--mbps N] [--verify-only]

model-00047 and model-00048 (189 GiB together) at the pinned revision go into CACHE_DIR, a
directory of their own, never the serving model directory: that one holds this node's sparse
slice under the same file names. Each shard's full sha256 is checked against the LFS oid in
weights/manifest-dba1be0a.tsv and stamped as <shard>.sha256; engram-slice.py refuses to cut
from a shard without that stamp.

The download resumes from a .partial file. It is streamed through sha256 as it arrives
(a resumed file is re-hashed first), flushed and dropped from the page cache every GiB, and
can be rate-limited with --mbps so it can run next to a serving engine without taking its
memory: on GB10 the page cache is the GPU's pool.
"""
import argparse
import hashlib
import os
import sys
import time
import urllib.request

REPO = "deepseek-ai/DeepSeek-V4.1-Flash"
PIN = "dba1be0a40aa45a94ad051997016db3960a90277"
SHARDS = ("model-00047-of-00048.safetensors", "model-00048-of-00048.safetensors")
CHUNK = 16 << 20

ap = argparse.ArgumentParser()
ap.add_argument("cache_dir")
ap.add_argument("--mbps", type=float, default=0, help="rate limit in MB/s, 0 for none")
ap.add_argument("--verify-only", action="store_true", help="only check the stamps; exit 1 if missing")
args = ap.parse_args()

manifest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest-dba1be0a.tsv")
rows = {p: (int(size), oid) for p, size, oid in (l.rstrip("\n").split("\t") for l in open(manifest))}


def log(msg):
    print(msg, flush=True)


def stamped(shard):
    path, stamp = os.path.join(args.cache_dir, shard), os.path.join(args.cache_dir, shard + ".sha256")
    size, oid = rows[shard]
    return (os.path.exists(path) and os.path.getsize(path) == size and os.path.exists(stamp)
            and open(stamp).read().split()[0] == oid)


if args.verify_only:
    missing = [s for s in SHARDS if not stamped(s)]
    for s in missing:
        log(f"not verified: {args.cache_dir}/{s}")
    sys.exit(1 if missing else 0)

os.makedirs(args.cache_dir, exist_ok=True)
need = sum(rows[s][0] for s in SHARDS if not stamped(s))
free = os.statvfs(args.cache_dir).f_bavail * os.statvfs(args.cache_dir).f_frsize
have = sum(os.path.getsize(os.path.join(args.cache_dir, s + ".partial"))
           for s in SHARDS if os.path.exists(os.path.join(args.cache_dir, s + ".partial")))
if need - have > free:
    sys.exit(f"{args.cache_dir}: {free / 2**30:.0f} GiB free, need {(need - have) / 2**30:.0f} GiB more")

for shard in SHARDS:
    size, oid = rows[shard]
    if stamped(shard):
        log(f"{shard}: already verified")
        continue
    path, part = os.path.join(args.cache_dir, shard), os.path.join(args.cache_dir, shard + ".partial")
    fd = os.open(part, os.O_RDWR | os.O_CREAT, 0o644)
    h, done = hashlib.sha256(), os.fstat(fd).st_size
    if done:
        log(f"{shard}: re-hashing {done / 2**30:.1f} GiB already on disk")
        for off in range(0, done, CHUNK):
            h.update(os.pread(fd, min(CHUNK, done - off), off))
            os.posix_fadvise(fd, off, CHUNK, os.POSIX_FADV_DONTNEED)
    url = f"https://huggingface.co/{REPO}/resolve/{PIN}/{shard}"
    started, got, since, last_log = time.time(), 0, 0, 0
    while done < size:
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes={done}-{size - 1}"})
            with urllib.request.urlopen(req, timeout=300) as r:
                if r.status not in (200, 206) or (done and r.status != 206):
                    raise OSError(f"HTTP {r.status} for bytes={done}-")
                while done < size:
                    buf = r.read(CHUNK)
                    if not buf:
                        break
                    os.pwrite(fd, buf, done)
                    h.update(buf)
                    done += len(buf)
                    got += len(buf)
                    since += len(buf)
                    if since >= 1 << 30:
                        os.fdatasync(fd)
                        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                        since = 0
                    if args.mbps:
                        lag = got / (args.mbps * 1e6) - (time.time() - started)
                        if lag > 0:
                            time.sleep(lag)
                    if done - last_log >= 8 << 30:
                        last_log = done
                        rate = got / max(time.time() - started, 1e-3) / 1e6
                        log(f"{shard}: {done / 2**30:6.1f} / {size / 2**30:.1f} GiB  {rate:5.0f} MB/s")
        except Exception as e:  # noqa: BLE001  resume from what is on disk
            log(f"{shard}: {type(e).__name__}: {e}; resuming at {done / 2**30:.1f} GiB in 10 s")
            os.fdatasync(fd)
            time.sleep(10)
    os.fdatasync(fd)
    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    os.close(fd)
    if h.hexdigest() != oid:
        os.replace(part, part + ".bad")
        sys.exit(f"{shard}: sha256 {h.hexdigest()} != manifest {oid}; kept as {part}.bad")
    os.replace(part, path)
    with open(path + ".sha256", "w") as f:
        f.write(f"{oid}  {shard}\n")
    log(f"{shard}: verified ({size / 2**30:.1f} GiB, sha256 matches the manifest)")
