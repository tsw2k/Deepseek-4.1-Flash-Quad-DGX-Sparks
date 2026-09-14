#!/usr/bin/env python3
"""Download the files of a pinned Hugging Face revision that this cluster does not already have.

usage: fetch-files.py MANIFEST DEST_DIR --repo OWNER/NAME --revision SHA [--only new|all] [--mbps N]

MANIFEST is a TSV written from the Hugging Face tree API at a pinned revision:
    path <TAB> size <TAB> sha256 (LFS) or git:<blob sha1> <TAB> status
where status is "new" or "same-as-release" (the file is byte-identical to a file of the release
checkpoint we already hold, so it is hardlinked, never downloaded again). With --only new
(default) only "new" rows are fetched.

Each file is streamed through its hash as it arrives, resumes from a .partial, is flushed and
dropped from the page cache every GiB (on GB10 the page cache is the GPU's memory), and is
renamed into place only when its hash matches the manifest. A verified file gets a
<path>.verified stamp holding the hash, so a re-run skips it.
"""
import argparse
import hashlib
import os
import sys
import time
import urllib.request

CHUNK = 16 << 20

ap = argparse.ArgumentParser()
ap.add_argument("manifest")
ap.add_argument("dest")
ap.add_argument("--repo", required=True)
ap.add_argument("--revision", required=True)
ap.add_argument("--only", choices=("new", "all"), default="new")
ap.add_argument("--mbps", type=float, default=0)
args = ap.parse_args()


def log(msg):
    print(msg, flush=True)


rows = []
for line in open(args.manifest):
    path, size, want, status = line.rstrip("\n").split("\t")
    if args.only == "all" or status == "new":
        rows.append((path, int(size), want))

need = sum(s for p, s, _ in rows if not os.path.exists(os.path.join(args.dest, p + ".verified")))
os.makedirs(args.dest, exist_ok=True)
st = os.statvfs(args.dest)
if need > st.f_bavail * st.f_frsize:
    sys.exit(f"{args.dest}: {st.f_bavail * st.f_frsize / 2**30:.0f} GiB free, need up to {need / 2**30:.0f} GiB")
log(f"{len(rows)} files, {need / 2**30:.1f} GiB to fetch into {args.dest}")

started, got_total = time.time(), 0
for path, size, want in rows:
    out = os.path.join(args.dest, path)
    stamp = out + ".verified"
    if os.path.exists(stamp) and open(stamp).read().strip() == want and os.path.getsize(out) == size:
        continue
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    part = out + ".partial"
    fd = os.open(part, os.O_RDWR | os.O_CREAT, 0o644)
    done = os.fstat(fd).st_size
    git = want.startswith("git:")
    h = hashlib.sha1(b"blob %d\0" % size) if git else hashlib.sha256()
    for off in range(0, done, CHUNK):
        h.update(os.pread(fd, min(CHUNK, done - off), off))
        os.posix_fadvise(fd, off, CHUNK, os.POSIX_FADV_DONTNEED)
    url = f"https://huggingface.co/{args.repo}/resolve/{args.revision}/{path}"
    since = 0
    while done < size:
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes={done}-{size - 1}"} if done else {})
            with urllib.request.urlopen(req, timeout=300) as r:
                if done and r.status != 206:
                    raise OSError(f"HTTP {r.status} on resume")
                while done < size:
                    buf = r.read(CHUNK)
                    if not buf:
                        break
                    os.pwrite(fd, buf, done)
                    h.update(buf)
                    done += len(buf)
                    got_total += len(buf)
                    since += len(buf)
                    if since >= 1 << 30:
                        os.fdatasync(fd)
                        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                        since = 0
                    if args.mbps:
                        lag = got_total / (args.mbps * 1e6) - (time.time() - started)
                        if lag > 0:
                            time.sleep(lag)
        except Exception as e:  # noqa: BLE001  resume from what is on disk
            log(f"{path}: {type(e).__name__}: {e}; resuming at {done / 2**30:.2f} GiB in 10 s")
            os.fdatasync(fd)
            time.sleep(10)
    os.fdatasync(fd)
    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    os.close(fd)
    got = ("git:" + h.hexdigest()) if git else h.hexdigest()
    if got != want:
        os.replace(part, part + ".bad")
        sys.exit(f"{path}: hash {got} != manifest {want}; kept as {part}.bad")
    os.replace(part, out)
    with open(stamp, "w") as f:
        f.write(want + "\n")
    rate = got_total / max(time.time() - started, 1e-3) / 1e6
    log(f"{path}: verified ({size / 2**30:.2f} GiB); {got_total / 2**30:.1f} GiB so far at {rate:.0f} MB/s")
log(f"done: {len(rows)} files verified in {args.dest}")
