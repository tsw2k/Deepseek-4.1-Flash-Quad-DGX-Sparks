#!/usr/bin/env python3
"""Pull the files of a manifest from another node's rsyncd over rail B, and verify each one.

usage: pull-files.py MANIFEST DEST_DIR --source rsync://RAIL_B_IP/models/REL [--only new|all]
                     [--bwlimit 400m]

The receiving half of fanning a download out (fetch-files.py fetched it once, on one node).
MANIFEST is the same TSV fetch-files.py reads. One file at a time: rsync --inplace --partial
writes it, this process keeps the file out of the page cache while it lands (on GB10 the page
cache is the GPU's memory), then hashes it with the cache dropped per chunk and writes the
<path>.verified stamp. A re-run skips stamped files and resumes a partial one.

The sending node keeps its side out of the cache with `pagecache-sweep.py SRC_DIR --idle 300`.
"""
import argparse
import hashlib
import os
import subprocess
import sys
import time

CHUNK = 64 << 20

ap = argparse.ArgumentParser()
ap.add_argument("manifest")
ap.add_argument("dest")
ap.add_argument("--source", required=True)
ap.add_argument("--only", choices=("new", "all"), default="new")
ap.add_argument("--bwlimit", default="400m")
args = ap.parse_args()


def log(msg):
    print(f"[{time.strftime('%H:%M:%S', time.gmtime())}] {msg}", flush=True)


def drop(path):
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    finally:
        os.close(fd)


def digest(path, size, want):
    git = want.startswith("git:")
    h = hashlib.sha1(b"blob %d\0" % size) if git else hashlib.sha256()
    fd = os.open(path, os.O_RDONLY)
    try:
        for off in range(0, size, CHUNK):
            h.update(os.pread(fd, min(CHUNK, size - off), off))
            os.posix_fadvise(fd, off, CHUNK, os.POSIX_FADV_DONTNEED)
    finally:
        os.close(fd)
    return ("git:" + h.hexdigest()) if git else h.hexdigest()


rows = []
for line in open(args.manifest):
    path, size, want, status = line.rstrip("\n").split("\t")
    if args.only == "all" or status == "new":
        rows.append((path, int(size), want))

todo = [r for r in rows if not (os.path.exists(os.path.join(args.dest, r[0] + ".verified"))
                                and open(os.path.join(args.dest, r[0] + ".verified")).read().strip() == r[2])]
need = sum(s for _, s, _ in todo)
os.makedirs(args.dest, exist_ok=True)
st = os.statvfs(args.dest)
if need > st.f_bavail * st.f_frsize:
    sys.exit(f"{args.dest}: {st.f_bavail * st.f_frsize / 2**30:.0f} GiB free, need up to {need / 2**30:.0f} GiB")
log(f"{len(rows)} files, {len(todo)} to pull ({need / 2**30:.1f} GiB) from {args.source}")

started, got = time.time(), 0
for path, size, want in todo:
    out = os.path.join(args.dest, path)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    for attempt in range(1, 6):
        p = subprocess.Popen(["rsync", "--inplace", "--partial", f"--bwlimit={args.bwlimit}",
                              f"{args.source}/{path}", out])
        while p.poll() is None:
            drop(out)
            time.sleep(2)
        drop(out)
        if p.returncode == 0:
            break
        log(f"{path}: rsync exit {p.returncode}, retry {attempt} in 10 s")
        time.sleep(10)
    else:
        sys.exit(f"{path}: rsync failed 5 times")
    if os.path.getsize(out) != size:
        sys.exit(f"{path}: size {os.path.getsize(out)} != manifest {size}")
    have = digest(out, size, want)
    if have != want:
        os.replace(out, out + ".bad")
        sys.exit(f"{path}: hash {have} != manifest {want}; kept as {out}.bad")
    with open(out + ".verified", "w") as f:
        f.write(want + "\n")
    got += size
    log(f"{path}: verified ({size / 2**30:.2f} GiB); {got / 2**30:.1f} GiB so far at "
        f"{got / max(time.time() - started, 1e-3) / 1e6:.0f} MB/s")
log(f"done: {len(rows)} files verified in {args.dest}")
