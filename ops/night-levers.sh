#!/usr/bin/env bash
# Lever runs at night, on the head, from dsv41-night.timer.
#
#   ops/night-levers.sh            run tonight's queue
#   ops/night-levers.sh --dry-run  print the plan and check the queue; starts and stops nothing
#
# Queue: $NIGHT_DIR/queue, one lever per line, values overriding cluster.env for that run only:
#   L3-k5-300k   SPEC_K=5 MAXLEN=300000
#   L5-minimal   PATCH_SET=minimal
# Blank lines and # comments are skipped. A lever that has run moves to $NIGHT_DIR/done.
# Two keys are for the runner, not the engine: NIGHT_NODE_START runs on every node once the lever
# is serving, NIGHT_NODE_STOP after its benchmark and whenever the night is cut short. Lever L6:
#   L6-flusher   NIGHT_NODE_START="sudo -n systemctl start glm53-flusher.service" NIGHT_NODE_STOP="sudo -n systemctl stop glm53-flusher.service"
# A line "@baseline" asks for a night of the baseline alone: one cold relaunch and one benchmark,
# for instance after the baseline itself changed in cluster.env (that change only takes effect at
# a relaunch).
#
# A night is A/B/A: the baseline, the lever, the baseline again, so each lever is read against two
# baselines taken the same night (a single run on this cluster drifts: docs/GOTCHAS.md). Further
# levers add B/A while the next pair still fits before DEADLINE. Every run starts cold: the GPUs
# at or below COOL_C, then a relaunch, so the prefix cache is empty; then bench/run.sh.
#
# Whatever happens, the night ends with the baseline serving and the watchdog armed (trap on EXIT).
# It does not start if the fleet is unhealthy, if the watchdog has given up, or if $NIGHT_DIR/pause
# exists. Do not `launch/cluster.sh ship` while it runs: it replaces the directory this runs from.
set -uo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
base_env=$root/cluster.env
# shellcheck source=/dev/null
source "$base_env"
dry=0; [ "${1:-}" = --dry-run ] && dry=1

NIGHT_DIR=${NIGHT_DIR:-/home/mtxc/dsv41-night}
TZ_LOCAL=${TZ_LOCAL:-Europe/Istanbul}   # the operator's clock; the nodes run UTC
DEADLINE=${DEADLINE:-05:00}             # local time by which the baseline serves again
COOL_C=${COOL_C:-60}
RUN_MIN=${RUN_MIN:-35}                  # relaunch + bench/run.sh, as measured
COOL_MIN=${COOL_MIN:-25}                # longest wait for the GPUs to cool
UNIT=dsv41-fleet.service
night=$(TZ=$TZ_LOCAL date +%F)
res=$NIGHT_DIR/results/$night
mkdir -p "$NIGHT_DIR/logs" "$NIGHT_DIR/run"; touch "$NIGHT_DIR/queue" "$NIGHT_DIR/done"
[ $dry = 1 ] || exec > >(tee -a "$NIGHT_DIR/logs/$night.log") 2>&1

say() { echo "[$(TZ=$TZ_LOCAL date +%H:%M)] $*"; }
on() { local n=$1; shift; if [ "$n" = "$(hostname)" ]; then bash -c "$*"; else ssh -o BatchMode=yes -o ConnectTimeout=15 "$n" "$@"; fi; }
deadline=$(TZ=$TZ_LOCAL date -d "$night $DEADLINE" +%s)
left_min() { echo $(( (deadline - $(date +%s)) / 60 )); }

# ---- the queue
levers=(); baseline_only=0
while IFS= read -r line; do
  line=${line%%#*}; [ -n "${line// }" ] || continue
  if [ "${line// }" = "@baseline" ]; then baseline_only=1; else levers+=("$line"); fi
done < "$NIGHT_DIR/queue"

mkenv() {  # mkenv NAME [KEY=VALUE ...] -> the env file, base cluster.env plus the overrides
  local f=$NIGHT_DIR/run/$1.env kv; shift
  cp "$base_env" "$f"
  { echo; echo "# night overrides"; for kv in "$@"; do printf '%s=%q\n' "${kv%%=*}" "${kv#*=}"; done; } >> "$f"
  echo "$f"
}

say "night $night: ${#levers[@]} lever(s) queued, deadline $DEADLINE $TZ_LOCAL ($(left_min) min left)"
for l in "${levers[@]}"; do
  read -r label rest <<< "$l"
  eval "kvs=($rest)"
  f=$(mkenv "$label" "${kvs[@]}")
  bash -n "$f" || { say "queue line for $label does not parse as shell: $l"; exit 2; }
  say "  $label: $(tail -n +$(( $(grep -n '^# night overrides' "$f" | cut -d: -f1) + 1 )) "$f" | tr '\n' ' ')"
done
per_lever=$(( 2 * (RUN_MIN + COOL_MIN) ))
say "plan: A, then B/A per lever while $per_lever min remain; first A needs $(( RUN_MIN + COOL_MIN )) min"
[ $baseline_only = 1 ] && say "@baseline queued: the baseline is relaunched and benchmarked once"
[ $dry = 1 ] && exit 0
[ ${#levers[@]} -gt 0 ] || [ $baseline_only = 1 ] || { say "queue empty: nothing tonight"; exit 0; }
[ ! -e "$NIGHT_DIR/pause" ] || { say "$NIGHT_DIR/pause exists: skipping tonight"; exit 0; }
need=$(( RUN_MIN + COOL_MIN )); [ ${#levers[@]} -gt 0 ] && need=$(( need + per_lever ))
[ "$(left_min)" -ge "$need" ] || { say "$(left_min) min before the deadline, $need needed: skipping tonight"; exit 0; }

# ---- only a healthy fleet is taken apart
healthy() {
  curl -sf -m 5 "http://$API_HOST:$API_PORT/health" >/dev/null || return 1
  for n in "${NODES[@]}"; do
    [ "$(on "$n" "docker inspect -f '{{.State.Status}}' '$CONTAINER'" 2>/dev/null)" = running ] || return 1
  done
}
healthy || { say "fleet not healthy at start: leaving it to the watchdog"; exit 1; }
[ ! -e /var/tmp/dsv41-watchdog.gaveup ] || { say "watchdog has given up: a person is needed, not a benchmark"; exit 1; }

cool() {
  local t0 max; t0=$(date +%s)
  while :; do
    max=$(for n in "${NODES[@]}"; do on "$n" "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader"; done | sort -rn | head -1)
    [ "${max:-99}" -le "$COOL_C" ] && { say "GPUs at most ${max} C"; return 0; }
    [ $(( $(date +%s) - t0 )) -lt $(( COOL_MIN * 60 )) ] || { say "GPUs still at ${max} C after $COOL_MIN min"; return 1; }
    sleep 60
  done
}
relaunch() {  # relaunch ENVFILE: every rank reads the same file, at the same path
  local f=$1 n
  for n in "${NODES[@]}"; do
    [ "$n" = "$(hostname)" ] || { on "$n" "mkdir -p '$NIGHT_DIR/run'" && scp -q "$f" "$n:$f"; } || return 1
  done
  export CLUSTER_ENV=$f NODE_CLUSTER_ENV=$f
  # shellcheck source=/dev/null
  if [ "$(source "$f"; echo "$PATCH_SET")" != "$PATCH_SET" ]; then bash "$root/launch/cluster.sh" render || return 1; fi
  bash "$root/launch/cluster.sh" down && bash "$root/launch/cluster.sh" up
}
node_hook() {  # node_hook ENVFILE START|STOP: the lever's runner-side command on every node
  local cmd n
  # shellcheck source=/dev/null
  cmd=$(source "$1"; v=NIGHT_NODE_$2; echo "${!v:-}")
  [ -n "$cmd" ] || return 0
  say "node hook $2 on every node: $cmd"
  for n in "${NODES[@]}"; do on "$n" "$cmd" || say "  $n: hook $2 failed"; done
}
lever_env=""
seq_no=0
bench() {  # bench LABEL ENVFILE
  seq_no=$((seq_no + 1))
  CLUSTER_ENV=$2 RESULTS_DIR=$res bash "$root/bench/run.sh" "$(printf '%02d' $seq_no)-$1"
}

serving=baseline
restore() {
  trap - EXIT
  [ -z "$lever_env" ] || node_hook "$lever_env" STOP
  if [ "$serving" != baseline ] || ! healthy; then
    say "restore: relaunching the baseline"
    unset NODE_CLUSTER_ENV; export CLUSTER_ENV=$base_env
    bash "$root/launch/cluster.sh" down; bash "$root/launch/cluster.sh" up || say "baseline did not come up; the watchdog takes over"
  fi
  sudo -n systemctl enable --now "$UNIT" && say "watchdog $UNIT armed; night over ($(left_min) min before the deadline)"
}

# ---- the night
sudo -n systemctl disable --now "$UNIT" || { say "cannot stop $UNIT; not touching the engine"; exit 1; }
trap restore EXIT
say "watchdog stopped for the night"
A=$(mkenv A-baseline)
cool || exit 1
relaunch "$A" || { serving=unknown; exit 1; }
bench A-baseline "$A" || say "baseline run failed its gates"
if [ $baseline_only = 1 ]; then
  printf '%s\t%s\t%s\t%s\n' "$night" ran "$res" "@baseline" >> "$NIGHT_DIR/done"
  grep -vx '[[:space:]]*@baseline[[:space:]]*' "$NIGHT_DIR/queue" > "$NIGHT_DIR/queue.new"; mv "$NIGHT_DIR/queue.new" "$NIGHT_DIR/queue"
fi

for l in "${levers[@]}"; do
  read -r label rest <<< "$l"
  [ "$(left_min)" -ge "$per_lever" ] || { say "$(left_min) min left, $label needs $per_lever: next night"; break; }
  eval "kvs=($rest)"; B=$(mkenv "$label" "${kvs[@]}")
  cool || break
  serving=lever
  if relaunch "$B"; then
    lever_env=$B; node_hook "$B" START
    bench "$label" "$B" || say "$label failed its gates"
    node_hook "$B" STOP; lever_env=""
    outcome=ran
  else
    say "$label did not boot"; outcome=boot-failed
  fi
  cool || break
  relaunch "$A" && serving=baseline || { serving=unknown; break; }
  bench A-baseline "$A" || say "baseline run failed its gates"
  printf '%s\t%s\t%s\t%s\n' "$night" "$outcome" "$res" "$l" >> "$NIGHT_DIR/done"
  grep -vxF "$l" "$NIGHT_DIR/queue" > "$NIGHT_DIR/queue.new" && mv "$NIGHT_DIR/queue.new" "$NIGHT_DIR/queue"
  say "$label: $outcome, recorded in $res"
done
