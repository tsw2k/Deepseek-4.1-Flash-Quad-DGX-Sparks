#!/usr/bin/env python3
"""Assemble a derived checkpoint directory from hardlinks, so no identical byte is stored twice.

usage: assemble-dir.py MANIFEST RELEASE_DIR NEW_DIR OUT_DIR [--replaced GLOB ...]

MANIFEST is the TSV fetch-files.py and pull-files.py read. "new" rows are linked from NEW_DIR
(which must hold their .verified stamps), "same-as-release" rows from RELEASE_DIR. Files of
RELEASE_DIR that the manifest does not list are linked too (engram-local.json, the per-rank
Engram slices' metadata, and the release's code directories), except those matching a
--replaced glob: the release tensors the derived checkpoint replaces. Nothing is copied and
nothing is removed; an OUT_DIR entry that already links to the right file is left alone, any
other existing entry is an error.

The Engram shards model-00047/48 are per-rank sparse slices on this cluster; they are linked
as they are, so run this on each node against that node's own release directory.
"""
import argparse
import fnmatch
import os
import sys

ap = argparse.ArgumentParser()
ap.add_argument("manifest")
ap.add_argument("release")
ap.add_argument("new")
ap.add_argument("out")
ap.add_argument("--replaced", action="append", default=[])
args = ap.parse_args()

links, listed = [], set()
for line in open(args.manifest):
    path, size, want, status = line.rstrip("\n").split("\t")
    listed.add(path)
    if status == "new":
        stamp = os.path.join(args.new, path + ".verified")
        if not os.path.exists(stamp) or open(stamp).read().strip() != want:
            sys.exit(f"{path}: not verified in {args.new}")
        links.append((os.path.join(args.new, path), path, int(size)))
    else:
        links.append((os.path.join(args.release, path), path, None))

for root, dirs, names in os.walk(args.release):
    dirs[:] = [d for d in dirs if d != ".cache"]
    for n in names:
        rel = os.path.relpath(os.path.join(root, n), args.release)
        if rel in listed or any(fnmatch.fnmatch(rel, g) for g in args.replaced):
            continue
        links.append((os.path.join(args.release, rel), rel, None))

made = kept = 0
for src, rel, size in links:
    dst = os.path.join(args.out, rel)
    s = os.stat(src)
    if size is not None and s.st_size != size:
        sys.exit(f"{src}: size {s.st_size} != manifest {size}")
    if os.path.lexists(dst):
        if os.stat(dst).st_ino == s.st_ino:
            kept += 1
            continue
        sys.exit(f"{dst} exists and is not a link to {src}")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    os.link(src, dst)
    made += 1
print(f"{args.out}: {made} links made, {kept} already in place, {len(links)} files")
