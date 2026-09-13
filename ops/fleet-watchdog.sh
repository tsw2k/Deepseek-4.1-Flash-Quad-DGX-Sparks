#!/usr/bin/env bash
# Fleet watchdog for the TP4 engine. Runs on the head (rank 0) as dsv41-fleet.service.
#
# Every CHECK_INTERVAL seconds it probes /health and runs the hang check. After FAIL_THRESHOLD
# consecutive failures of either kind it does a full orchestrated relaunch:
#   launch/cluster.sh down  (head first, every rank's log saved)
#   launch/cluster.sh up    (preflight, workers 3-2-1 then head, /health, Engram check)
#
# Why a full relaunch: vLLM cannot recover a dead engine core, a headless worker exits 0 when
# its head dies (so restart policies never fire), and a worker restarted alone joins a stale
# rendezvous. Same reasoning as the GLM-5.3 watchdog this replaces.
#
# Why /health and the hang check: /health returns 503 once the engine is dead, but a padded
# speculative batch stuck in sparse MLA (FlashInfer #5015) keeps /health at 200 while running
# requests produce nothing. ops/hangcheck.sh catches that.
#
# It stops trying after MAX_RECOVERIES failed relaunches in a row: a boot that keeps failing
# needs a person, and relaunching a wedged fleet every few minutes only hides the cause.
#
# Pause: /var/tmp/dsv41-watchdog.pause on the head. `cluster.sh down` run by hand creates it
# and a successful `cluster.sh up` removes it, so manual work is never undone behind your back.
set -u

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=/dev/null
source "${CLUSTER_ENV:-$root/cluster.env}"

CHECK_INTERVAL=${CHECK_INTERVAL:-60}
FAIL_THRESHOLD=${FAIL_THRESHOLD:-3}
MAX_RECOVERIES=${MAX_RECOVERIES:-3}
HEALTH_URL="http://$API_HOST:$API_PORT/health"
PAUSE_FLAG=/var/tmp/dsv41-watchdog.pause
GIVEUP_FLAG=/var/tmp/dsv41-watchdog.gaveup
LOG=${WATCHDOG_LOG:-/var/tmp/dsv41-logs/watchdog.log}
LOCK=/var/tmp/dsv41-watchdog.lock

mkdir -p "$(dirname "$LOG")"
log() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$LOG"; }

exec 9>"$LOCK"
flock -n 9 || { echo "watchdog already running ($LOCK)" >&2; exit 1; }

[ "$(hostname)" = "${NODES[0]}" ] || { log "not the head (${NODES[0]}); exiting"; exit 2; }

probe() {
  curl -sf -m 15 -o /dev/null "$HEALTH_URL" || { echo "health"; return 1; }
  bash "$root/ops/hangcheck.sh" "$CONTAINER" >/dev/null || { echo "hang"; return 1; }
  return 0
}

recover() {
  log "=== RECOVERY: $FAIL_THRESHOLD consecutive failures ($1)"
  WATCHDOG=1 bash "$root/launch/cluster.sh" down >> "$LOG" 2>&1
  sleep 10   # master port TIME_WAIT
  if WATCHDOG=1 bash "$root/launch/cluster.sh" up >> "$LOG" 2>&1; then
    log "=== RECOVERY OK"
    return 0
  fi
  log "=== RECOVERY FAILED (see the lines above; rank logs in /var/tmp/dsv41-logs/)"
  return 1
}

log "watchdog started: $HEALTH_URL every ${CHECK_INTERVAL}s, threshold $FAIL_THRESHOLD, max recoveries $MAX_RECOVERIES"
fails=0
failed_recoveries=0
while true; do
  if [ -f "$GIVEUP_FLAG" ]; then
    sleep "$CHECK_INTERVAL"; continue
  fi
  if [ -f "$PAUSE_FLAG" ]; then
    [ "$fails" -eq 0 ] || log "paused ($(cat "$PAUSE_FLAG")); failure count reset"
    fails=0
    sleep "$CHECK_INTERVAL"; continue
  fi
  if why=$(probe); then
    [ "$fails" -gt 0 ] && log "healthy again after $fails failure(s)"
    fails=0
    failed_recoveries=0
  else
    fails=$((fails + 1))
    log "probe failed ($why) $fails/$FAIL_THRESHOLD"
    if [ "$fails" -ge "$FAIL_THRESHOLD" ]; then
      if recover "$why"; then
        failed_recoveries=0
      else
        failed_recoveries=$((failed_recoveries + 1))
        if [ "$failed_recoveries" -ge "$MAX_RECOVERIES" ]; then
          echo "gave up at $(date -u +%FT%TZ) after $failed_recoveries failed relaunches" > "$GIVEUP_FLAG"
          log "=== GIVING UP after $failed_recoveries failed relaunches; remove $GIVEUP_FLAG to re-arm"
        fi
      fi
      fails=0
    fi
  fi
  sleep "$CHECK_INTERVAL"
done
