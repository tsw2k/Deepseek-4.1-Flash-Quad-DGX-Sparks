#!/usr/bin/env python3
"""Check a local checkpoint against the pinned Hugging Face manifest.

usage: verify.py MODEL_DIR [--size-only] [--jobs=N] [--manifest=TSV]

--manifest checks a derived checkpoint instead (weights/manifest-exl3-f129e31a.tsv).

weights/manifest-dba1be0a.tsv lists every file of deepseek-ai/DeepSeek-V4.1-Flash at revision
dba1be0a40aa45a94ad051997016db3960a90277: path, size, and either the LFS sha256 or, for small
git-tracked files, "git:<blob sha1>". Every file must match, except the two Engram shards
(model-00047/48), which are per-rank sparse slices on this cluster and are checked by
engram-slice.py against the rank recorded in engram-local.json.

Hashing drops each chunk from the page cache as it goes: on GB10 the cache is GPU memory.
"""
import hashlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor

ENGRAM_SHARDS = {"model-00047-of-00048.safetensors", "model-00048-of-00048.safetensors"}
CHUNK = 64 << 20

model_dir = sys.argv[1]
size_only = "--size-only" in sys.argv
jobs = int(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--jobs=")), "8"))
manifest = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--manifest=")),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest-dba1be0a.tsv"))


def digest(path: str, want: str) -> str:
    if want.startswith("git:"):
        data = open(path, "rb").read()
        return "git:" + hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    h = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY)
    try:
        off = 0
        while True:
            buf = os.pread(fd, CHUNK, off)
            if not buf:
                break
            h.update(buf)
            os.posix_fadvise(fd, off, len(buf), os.POSIX_FADV_DONTNEED)
            off += len(buf)
    finally:
        os.close(fd)
    return h.hexdigest()


def check(row):
    path, size, want = row
    full = os.path.join(model_dir, path)
    if not os.path.isfile(full):
        return path, "MISSING"
    got_size = os.path.getsize(full)
    if got_size != size:
        return path, f"SIZE {got_size} != {size}"
    if size_only:
        return path, None
    got = digest(full, want)
    return path, None if got == want else f"HASH {got} != {want}"


rows = []
for line in open(manifest):
    path, size, want = line.rstrip("\n").split("\t")[:3]  # derived manifests add a status column
    if path in ENGRAM_SHARDS:
        continue
    rows.append((path, int(size), want))

bad = 0
with ThreadPoolExecutor(max_workers=jobs) as ex:
    for path, err in ex.map(check, rows):
        if err:
            bad += 1
            print(f"FAIL {path}: {err}", flush=True)
mode = "sizes" if size_only else "sizes and hashes"
print(f"{len(rows) - bad}/{len(rows)} files match the manifest ({mode}); Engram shards checked separately")
sys.exit(1 if bad else 0)
