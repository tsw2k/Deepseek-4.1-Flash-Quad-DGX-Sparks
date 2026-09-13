#!/usr/bin/env bash
# Drive all four ranks from the operator host (anything that can `ssh spark-0N`).
#
#   launch/cluster.sh ship         git archive HEAD + cluster.env to REPO_DIR on every node
#   launch/cluster.sh render       render the patch set on every node and compare hashes
#   launch/cluster.sh slice        cut each node's Engram slice (weights/engram-slice.py)
#   launch/cluster.sh preflight    every launch check on every node, nothing started
#   launch/cluster.sh up           down-check, preflight, ranks 3,2,1 then 0, wait for /health
#   launch/cluster.sh down         head first, save each rank's log, remove the containers
#   launch/cluster.sh status       container state, /health, hang check
#   launch/cluster.sh engram       prove every rank reads its own Engram rows locally
#   launch/cluster.sh logs RANK [N]
#
# Order matters in both directions. Up: workers first, head last, all promptly. Down: head
# first. A worker that starts while an old head still listens on the master port joins that
# head's rendezvous and hangs the new boot (Tech2Wild/Kai, relaunch race).
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
env_file=${CLUSTER_ENV:-$root/cluster.env}
# shellcheck source=/dev/null
source "$env_file"
cmd=${1:?usage: cluster.sh ship|render|slice|preflight|up|down|status|engram|logs}

# Run a command on a node. On the node itself (the watchdog runs on the head) it runs locally:
# a node need not be able to ssh to itself.
on() {
  local n=$1; shift
  if [ "$n" = "$(hostname)" ]; then bash -c "$*"; else ssh -o BatchMode=yes -o ConnectTimeout=15 "$n" "$@"; fi
}
# Operator stops pause the watchdog (ops/fleet-watchdog.sh) until the next successful `up`;
# the watchdog's own recovery passes WATCHDOG=1 so it does not pause itself.
PAUSE_FLAG=/var/tmp/dsv41-watchdog.pause
node_env="CLUSTER_ENV=$REPO_DIR/cluster.env"

case "$cmd" in
ship)
  [ -z "$(git -C "$root" status --porcelain --untracked-files=no)" ] || echo "note: uncommitted changes are NOT shipped (git archive HEAD)" >&2
  rev=$(git -C "$root" rev-parse --short HEAD)
  for n in "${NODES[@]}"; do
    git -C "$root" archive --format=tar HEAD | on "$n" "rm -rf '$REPO_DIR.new' && mkdir -p '$REPO_DIR.new' && tar -x -C '$REPO_DIR.new' && echo $rev > '$REPO_DIR.new/REVISION'"
    on "$n" "cat > '$REPO_DIR.new/cluster.env'" < "$env_file"
    on "$n" "rm -rf '$REPO_DIR.old' && { [ ! -d '$REPO_DIR' ] || mv '$REPO_DIR' '$REPO_DIR.old'; } && mv '$REPO_DIR.new' '$REPO_DIR' && rm -rf '$REPO_DIR.old'"
    echo "$n: $REPO_DIR at $rev"
  done
  ;;
render)
  for n in "${NODES[@]}"; do
    on "$n" "bash '$REPO_DIR/patches/render.sh' '$PATCH_SET' '$PATCH_ROOT' && sha256sum '$PATCH_ROOT/$PATCH_SET/mounts.txt' '$PATCH_ROOT/$PATCH_SET/SHA256SUMS'" | sed "s#^#$n: #"
  done
  ;;
slice)
  pids=()
  for i in "${!NODES[@]}"; do
    ( set -o pipefail
      on "${NODES[$i]}" "python3 '$REPO_DIR/weights/engram-slice.py' '$MODEL_DIR' --rank $i --revision '$MODEL_REVISION'" 2>&1 \
        | sed "s#^#${NODES[$i]}: #" ) &
    pids+=($!)
  done
  bad=0
  for p in "${pids[@]}"; do wait "$p" || bad=1; done
  exit $bad
  ;;
preflight)
  bad=0
  for i in "${!NODES[@]}"; do
    on "${NODES[$i]}" "$node_env bash '$REPO_DIR/launch/node.sh' $i --preflight" || bad=1
  done
  ids=$(for n in "${NODES[@]}"; do on "$n" "docker image inspect '$IMAGE' --format '{{.Id}}'" 2>/dev/null || echo missing; done | sort -u)
  [ "$(echo "$ids" | wc -l)" -eq 1 ] || { echo "image IDs differ across nodes:"; echo "$ids"; bad=1; }
  revs=$(for n in "${NODES[@]}"; do on "$n" "cat '$REPO_DIR/REVISION'"; done | sort -u)
  [ "$(echo "$revs" | wc -l)" -eq 1 ] || { echo "recipe revisions differ across nodes: $revs"; bad=1; }
  [ $bad -eq 0 ] && echo "preflight passed on all ranks (image $ids, recipe $revs)"
  exit $bad
  ;;
up)
  for n in "${NODES[@]}"; do
    if on "$n" "docker container inspect '$CONTAINER' >/dev/null 2>&1"; then
      echo "$n still has $CONTAINER; run cluster.sh down first" >&2; exit 3
    fi
  done
  "$0" preflight
  for i in 3 2 1 0; do
    on "${NODES[$i]}" "$node_env LEVER_ENV='${LEVER_ENV:-}' VLLM_EXTRA='${VLLM_EXTRA:-}' bash '$REPO_DIR/launch/node.sh' $i"
  done
  echo "waiting for http://$API_HOST:$API_PORT/health (weights, draft, autotune and graph capture take many minutes)"
  t0=$(date +%s)
  until on "${NODES[0]}" "curl -sf -m 5 http://$API_HOST:$API_PORT/health >/dev/null"; do
    for n in "${NODES[@]}"; do
      state=$(on "$n" "docker inspect -f '{{.State.Status}}' '$CONTAINER'" 2>/dev/null || echo gone)
      [ "$state" = running ] || { echo "$n: $CONTAINER is $state"; on "$n" "docker logs --tail 60 '$CONTAINER'" >&2; exit 1; }
    done
    [ $(( $(date +%s) - t0 )) -lt 3600 ] || { echo "no /health after 60 min" >&2; exit 1; }
    sleep 30
  done
  echo "serving after $(( ($(date +%s) - t0) / 60 )) min"
  "$0" engram
  on "${NODES[0]}" "rm -f $PAUSE_FLAG"
  ;;
down)
  if [ "${WATCHDOG:-0}" != 1 ]; then
    on "${NODES[0]}" "echo 'paused by cluster.sh down at $(date -u +%FT%TZ)' > $PAUSE_FLAG"
    echo "watchdog paused ($PAUSE_FLAG on ${NODES[0]}) until the next successful up"
  fi
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  for n in "${NODES[0]}" "${NODES[3]}" "${NODES[2]}" "${NODES[1]}"; do
    on "$n" "if docker container inspect '$CONTAINER' >/dev/null 2>&1; then
               mkdir -p /var/tmp/dsv41-logs/$ts && docker logs -t '$CONTAINER' > /var/tmp/dsv41-logs/$ts/\$(hostname).log 2>&1
               docker inspect '$CONTAINER' > /var/tmp/dsv41-logs/$ts/\$(hostname).inspect.json
               docker rm -f '$CONTAINER' >/dev/null && echo \"\$(hostname): stopped, log in /var/tmp/dsv41-logs/$ts\"
             else echo \"\$(hostname): no container\"; fi"
  done
  ;;
status)
  for n in "${NODES[@]}"; do
    echo "$n: $(on "$n" "docker ps -a --filter name=^$CONTAINER\$ --format '{{.Status}} {{.Image}}'; bash '$REPO_DIR/ops/hangcheck.sh' '$CONTAINER' || true" | paste -sd' ' -)"
  done
  on "${NODES[0]}" "curl -sf -m 5 http://$API_HOST:$API_PORT/health >/dev/null && echo health: ok || echo health: down"
  ;;
engram)
  bad=0
  for i in "${!NODES[@]}"; do
    out=$(on "${NODES[$i]}" "docker logs '$CONTAINER' 2>&1 | grep -E 'Engram layer|Engram DISK mode|DSV41_ENGRAM_DIR' | sort -u")
    locals=$(grep -c 'read from node-local' <<< "$out" || true)
    warns=$(grep -cE 'unusable|this rank needs' <<< "$out" || true)
    echo "${NODES[$i]} rank $i: $locals tables read node-local, $warns warnings"
    [ "$locals" -ge 2 ] && [ "$warns" -eq 0 ] || { echo "$out"; bad=1; }
  done
  exit $bad
  ;;
logs)
  r=${2:?rank}
  on "${NODES[$r]}" "docker logs --tail ${3:-200} '$CONTAINER'"
  ;;
*)
  echo "unknown command: $cmd" >&2; exit 2 ;;
esac
