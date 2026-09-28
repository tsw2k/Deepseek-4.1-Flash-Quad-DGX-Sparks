#!/usr/bin/env bash
# Guard one engine container against GB10 unified-memory exhaustion, for the container's lifetime.
#
#   sudo ops/memguard.sh CONTAINER            started by launch/node.sh right after docker run
#
# On a GB10 the GPU allocates from the host's memory. When that pool runs out the kernel cannot take
# GPU memory back: userland starves while the kernel still answers ping, and the node needs a power
# cycle (results/2026-09-26-nvfp4-incident: three nodes, 53 hours). The guard reads /proc/meminfo once
# a second and, in enforce mode, kills the container's init process the moment MemAvailable falls
# below the floor, so a boot that would have hung the node fails cleanly instead. It kills by PID,
# not through dockerd, which may itself be starved by then. The other ranks then wait in a collective
# until launch/cluster.sh or the watchdog notices the missing rank.
#
# Modes (MEMGUARD_MODE in cluster.env, read by node.sh): observe logs the lowest values only;
# enforce also kills; off does not start. Every run writes /var/tmp/dsv41-logs/memguard-*.log; a
# trip also writes /var/tmp/dsv41-memguard.tripped, which the head reads and reports.
set -u
c=${1:?usage: memguard.sh CONTAINER}
mode=${MEMGUARD_MODE:-observe}
floor_mib=$(( ${MEMGUARD_FLOOR_GIB:-4} * 1024 ))
logdir=/var/tmp/dsv41-logs; mkdir -p "$logdir"
log=$logdir/memguard-$(date -u +%Y%m%dT%H%M%SZ).log
mark=/var/tmp/dsv41-memguard.tripped
echo -1000 > /proc/self/oom_score_adj 2>/dev/null || true
renice -n -10 $$ >/dev/null 2>&1 || true
say() { echo "$(date -u +%FT%TZ) $*" >> "$log"; }

pid=""
for _ in $(seq 1 60); do
  pid=$(docker inspect -f '{{.State.Pid}}' "$c" 2>/dev/null) && [ -n "$pid" ] && [ "$pid" != 0 ] && break
  pid=""; sleep 1
done
[ -n "$pid" ] || { say "no running $c after 60 s; not guarding"; exit 0; }
rm -f "$mark"
say "guarding $c (pid $pid), mode $mode, floor $((floor_mib / 1024)) GiB MemAvailable"

min_avail=999999999; min_free=999999999; last_gib=-1; t0=$(date +%s)
while kill -0 "$pid" 2>/dev/null; do
  read -r avail free < <(awk '/^MemAvailable:/ {a=int($2/1024)} /^MemFree:/ {f=int($2/1024)} END {print a, f}' /proc/meminfo)
  [ "$free" -lt "$min_free" ] && min_free=$free
  if [ "$avail" -lt "$min_avail" ]; then
    min_avail=$avail
    # one line per GiB of new low, so a boot's memory curve is in the log without a line a second
    [ $((avail / 1024)) -ne "$last_gib" ] && { last_gib=$((avail / 1024)); say "low: MemAvailable ${avail} MiB, MemFree ${free} MiB, t+$(( $(date +%s) - t0 )) s"; }
  fi
  if [ "$avail" -lt "$floor_mib" ]; then
    if [ "$mode" = enforce ]; then
      kill -9 "$pid" 2>/dev/null
      msg="memguard TRIPPED on $(hostname): MemAvailable ${avail} MiB < floor $((floor_mib / 1024)) GiB at t+$(( $(date +%s) - t0 )) s; killed $c (pid $pid)"
      say "$msg"; echo "$msg" > "$mark"
      exit 1
    fi
    [ "${warned:-0}" = 1 ] || { say "observe: MemAvailable ${avail} MiB below the floor (enforce would have killed $c)"; warned=1; }
  fi
  sleep 1
done
say "container gone after $(( $(date +%s) - t0 )) s; lowest MemAvailable ${min_avail} MiB, lowest MemFree ${min_free} MiB"
