#!/usr/bin/env bash
# One recorded run: configuration snapshot, correctness gates, then the fixed-prompt benchmark
# and the needle test. Numbers without the configuration that produced them are not kept.
#
#   bench/run.sh LABEL [--gates-only]         # from the operator host, cluster serving
#
# Results land in results/<UTC date>-<LABEL>/ on the operator host. The client runs on the
# head against the rail A address: those requests never touch a wire, and the fixed prompt
# set, token budgets and timing rules are Tech2Wild/Kai's (bench/tony/, byte-identical), so
# the numbers compare directly with boot 10 and with 0xTank's 600K/K3 run.
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=/dev/null
source "${CLUSTER_ENV:-$root/cluster.env}"
label=${1:?usage: run.sh LABEL [--gates-only]}
# RESULTS_DIR: ops/night-levers.sh keeps its runs outside the shipped recipe directory.
out="${RESULTS_DIR:-$root/results}/$(date -u +%Y-%m-%d)-$label"
[ ! -e "$out" ] || { echo "$out exists" >&2; exit 2; }
mkdir -p "$out"
head=${NODES[0]}
base="http://$API_HOST:$API_PORT/v1"
# On the head itself (the night runner) commands run locally: a node need not ssh to itself.
on() { local n=$1; shift; if [ "$n" = "$(hostname)" ]; then bash -c "$*"; else ssh -o BatchMode=yes "$n" "$@"; fi; }
fetch() { if [ "$head" = "$(hostname)" ]; then cp -r "$1" "$2"; else scp -q -r "$head:$1" "$2"; fi; }

# ---- snapshot: what exactly is serving
{
  echo "label: $label"
  echo "utc: $(date -u +%FT%TZ)"
  echo "recipe: $(on "$head" "cat '$REPO_DIR/REVISION'")"
  echo "operator-git: $(git -C "$root" rev-parse HEAD 2>/dev/null || echo "none (run from the shipped recipe)") $(git -C "$root" status --porcelain --untracked-files=no 2>/dev/null | wc -l) uncommitted"
} > "$out/run.txt"
cp "${CLUSTER_ENV:-$root/cluster.env}" "$out/cluster.env"
for i in "${!NODES[@]}"; do
  n=${NODES[$i]}
  on "$n" "docker inspect '$CONTAINER'" > "$out/inspect-rank$i.json"
  on "$n" "cat '$PATCH_ROOT/$PATCH_SET/SHA256SUMS'" > "$out/patches-rank$i.sha256"
  on "$n" "nvidia-smi --query-gpu=name,driver_version,temperature.gpu,power.draw,clocks.current.graphics --format=csv; uname -r; cat /proc/meminfo | head -5; sysctl vm.min_free_kbytes vm.watermark_scale_factor; systemctl is-active glm53-flusher.service || true" > "$out/host-rank$i.txt" 2>&1
done
python3 - "$out" <<'PY'
import json, sys, glob
out = sys.argv[1]
rows = []
for f in sorted(glob.glob(f"{out}/inspect-rank*.json")):
    c = json.load(open(f))[0]
    env = dict(e.split("=", 1) for e in c["Config"]["Env"])
    rows.append((f.split("rank")[-1][0], c["Image"][:19], c["Config"]["Labels"].get("dsv41.gid_index"),
                 env.get("NCCL_IB_TC"), env.get("DSV41_COMPACT_O_PROJ"), " ".join(c["Args"])))
with open(f"{out}/run.txt", "a") as fh:
    for r in rows:
        fh.write("rank %s image %s gid %s tc %s compact_o_proj %s\n" % r[:5])
    fh.write("args(rank0): %s\n" % rows[0][5])
    same = len({r[1] for r in rows}) == 1
    fh.write(f"image identical across ranks: {same}\n")
PY
# Which kernels the engine actually chose: a lever that fails to select its kernel otherwise
# measures the next one in the list without saying so.
on "$head" "docker logs '$CONTAINER' 2>&1 | grep -oE 'Using [A-Za-z0-9]+ for [A-Z0-9]+ GEMM' | sort -u" >> "$out/run.txt" 2>/dev/null || true
cat "$out/run.txt"

# ---- gates first; a failed gate stops the run
rdir="/var/tmp/dsv41-bench/$(basename "$out")"
on "$head" "mkdir -p '$rdir'"
set +e
on "$head" "python3 '$REPO_DIR/bench/gates.py' --base '$base' --out '$rdir/gates.json'"
gates_rc=$?
set -e
fetch "$rdir/gates.json" "$out/" || true
[ $gates_rc -eq 0 ] || { echo "gates failed: no benchmark recorded for a model that fails correctness" >&2; exit 1; }

# ---- numeric check: has the distribution moved since the reference run?
# Gates pass on a model that answers and formats; they say nothing about its logits. Set
# QUALITY_REF=none to skip, or to another reference run directory on the head.
qref=${QUALITY_REF:-/home/mtxc/dsv41-quality/release-a}
if [ "$qref" != none ] && on "$head" "test -f '$qref/meta.json'"; then
  set +e
  on "$head" "cd '$(dirname "$qref")' && python3 '$REPO_DIR/bench/quality.py' probe '$qref' \
    --base 'http://$API_HOST:$API_PORT' --windows ${QUALITY_WINDOWS:-10} --report '$rdir/quality-probe.json'" \
    | tee "$out/quality-probe.txt"
  qrc=${PIPESTATUS[0]}
  set -e
  fetch "$rdir/quality-probe.json" "$out/" 2>/dev/null || true
  echo "quality probe: $([ "$qrc" -eq 0 ] && echo within thresholds || echo OUTSIDE THRESHOLDS) (reference $qref)" >> "$out/run.txt"
  [ "$qrc" -eq 0 ] || echo "WARNING: the engine's next-token distribution has moved from $qref; see $out/quality-probe.txt" >&2
else
  echo "quality probe: skipped (no reference at $qref)" >> "$out/run.txt"
fi

[ "${2:-}" = --gates-only ] && exit 0

# ---- benchmark and needle
on "$head" "cd '$rdir' && python3 '$REPO_DIR/bench/tony/v41bench.py' --base '$base' --label '$label' --out '$rdir' \
  --levels 1,2,3,4,5,6 --prefill 2000,8000,32000,64000 --notes 'set=$PATCH_SET k=$SPEC_K maxlen=$MAXLEN gmu=$GMU lever_env=${LEVER_ENV:-none} draft=${DRAFT_SAMPLE:-probabilistic} spec=${SPEC:-dspark}'"
on "$head" "bash '$REPO_DIR/ops/hangcheck.sh' '$CONTAINER'" || true
on "$head" "cd '$rdir' && python3 '$REPO_DIR/bench/tony/v41needle.py' --base '$base' --targets 131072 --depth 0.5 --out '$rdir/needle-131k.json'"
fetch "$rdir/." "$out/"
on "$head" "docker logs '$CONTAINER' 2>&1 | grep 'SpecDecoding metrics'" > "$out/spec-decode.log" || true
[ -s "$out/spec-decode.log" ] || echo "warning: no SpecDecoding metrics captured" >&2
echo "recorded in $out"
