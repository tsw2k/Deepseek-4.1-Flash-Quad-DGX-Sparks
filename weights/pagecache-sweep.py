#!/usr/bin/env python3
"""Keep one file out of the page cache while another process reads or writes it.

usage: pagecache-sweep.py FILE [--wait 120] [--every 2]

Runs next to a transfer the sweeper does not control, such as rsyncd sending a slice pack or
the rsync client receiving it. Every --every seconds it asks the kernel to drop the file's
clean pages. It waits up to --wait seconds for some process to open the file, and exits once
no process has had it open for 10 seconds. It needs no cooperation from the transfer: it only
looks at /proc/*/fd.

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
args = ap.parse_args()
target = os.path.abspath(args.file)


def held():
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            for fd in os.listdir(f"/proc/{pid}/fd"):
                try:
                    link = os.readlink(f"/proc/{pid}/fd/{fd}")
                except OSError:
                    continue
                # rsync writes to a temporary sibling (.name.XXXXXX) unless --inplace
                if link == target or link.startswith(os.path.join(os.path.dirname(target), "." + os.path.basename(target))):
                    return True
        except OSError:
            continue
    return False


def sweep():
    d, base = os.path.dirname(target), os.path.basename(target)
    try:
        names = [n for n in os.listdir(d) if n == base or n.startswith("." + base)]
    except OSError:
        return
    for n in names:
        try:
            fd = os.open(os.path.join(d, n), os.O_RDONLY)
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
        if time.time() - idle_since >= 10:
            break
    elif time.time() - start > args.wait:
        break
    time.sleep(args.every)
sweep()
