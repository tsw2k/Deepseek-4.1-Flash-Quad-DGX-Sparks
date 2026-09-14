#!/usr/bin/env python3
"""Keep a file, or every file under a directory, out of the page cache while another process
reads or writes it.

usage: pagecache-sweep.py FILE|DIR [--wait 120] [--every 2] [--idle 10]

Runs next to a transfer the sweeper does not control, such as rsyncd sending a slice pack or
the rsync client receiving it. Every --every seconds it asks the kernel to drop the clean pages
of the file (or of every file under DIR). It waits up to --wait seconds for some process to open
the file (or anything under DIR), and exits once nothing has been open for --idle seconds. It
needs no cooperation from the transfer: it only looks at /proc/*/fd. DIR mode is for the sending
node of a many-file pull (pull-files.py); give it an --idle longer than the receiver's hash of
one file.

On GB10 the page cache is the GPU's memory, so a 47.5 GiB pack cached on a serving node is
47.5 GiB the engine cannot have.
"""
import argparse
import os
import time

ap = argparse.ArgumentParser()
ap.add_argument("file")
ap.add_argument("--wait", type=float, default=120)
ap.add_argument("--every", type=float, default=2)
ap.add_argument("--idle", type=float, default=10)
args = ap.parse_args()
target = os.path.abspath(args.file)
is_dir = os.path.isdir(target)


def matches(link):
    if is_dir:
        return link.startswith(target + "/")
    # rsync writes to a temporary sibling (.name.XXXXXX) unless --inplace
    return link == target or link.startswith(os.path.join(os.path.dirname(target), "." + os.path.basename(target)))


def held():
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            for fd in os.listdir(f"/proc/{pid}/fd"):
                try:
                    if matches(os.readlink(f"/proc/{pid}/fd/{fd}")):
                        return True
                except OSError:
                    continue
        except OSError:
            continue
    return False


def paths():
    if is_dir:
        for root, _, names in os.walk(target):
            for n in names:
                yield os.path.join(root, n)
        return
    d, base = os.path.dirname(target), os.path.basename(target)
    try:
        names = [n for n in os.listdir(d) if n == base or n.startswith("." + base)]
    except OSError:
        return
    for n in names:
        yield os.path.join(d, n)


def sweep():
    for p in paths():
        try:
            fd = os.open(p, os.O_RDONLY)
        except OSError:
            continue
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)


start, seen, idle_since = time.time(), False, None
while True:
    sweep()
    if held():
        seen, idle_since = True, None
    elif seen:
        idle_since = idle_since or time.time()
        if time.time() - idle_since >= args.idle:
            break
    elif time.time() - start > args.wait:
        break
    time.sleep(args.every)
sweep()
