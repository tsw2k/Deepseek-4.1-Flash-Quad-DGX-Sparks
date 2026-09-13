#!/usr/bin/env bash
# Start one TP4 rank on this node.
#
#   bash launch/node.sh RANK [--preflight|--dry-run]
#
# Normally called by launch/cluster.sh, which starts ranks 3, 2, 1 and then 0. --preflight runs
# every check and starts nothing; --dry-run also prints the docker command.
#
# The vLLM command line and environment are 0xTank's measured 600K/K3 configuration
# (itself Tech2Wild/Kai's boot 10 plus three switches). Deviations forced by this cluster, and
# nothing else:
#   - NCCL_IB_TC: the switch's PFC class
#   - the RoCEv2 GID index is looked up from sysfs, never pinned (it moves between reboots)
#   - no NFS: every rank has shards 1-46 locally and its own sparse Engram slice in the model
#     directory, so DSV41_ENGRAM_DIR points there on every rank, head included
#   - nofile is raised on the container itself
set -euo pipefail

rank=${1:?usage: node.sh RANK [--preflight|--dry-run]}
mode=${2:-run}
[[ $rank =~ ^[0-3]$ ]] || { echo "rank must be 0..3" >&2; exit 2; }
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=/dev/null
source "${CLUSTER_ENV:-$root/cluster.env}"

fail() { echo "PREFLIGHT FAIL [rank $rank $(hostname)]: $*" >&2; exit 5; }
note() { echo "  ok: $*"; }

# ---- this node is the rank it claims to be
[ "$(hostname)" = "${NODES[$rank]}" ] || fail "hostname $(hostname) but rank $rank is ${NODES[$rank]}"
my_ip=${RAIL_A_IPS[$rank]}
ip -4 -o addr show dev "$RAIL_A_IFACE" | grep -q " $my_ip/" || fail "$my_ip is not on $RAIL_A_IFACE"
[ "$(cat "/sys/class/net/$RAIL_A_IFACE/operstate")" = up ] || fail "$RAIL_A_IFACE is not up"
note "$(hostname) rank $rank, rail A $my_ip on $RAIL_A_IFACE"

# ---- RoCEv2 GID of the rail A address, from sysfs
want_gid=$(printf '0000:0000:0000:0000:0000:ffff:%02x%02x:%02x%02x' ${my_ip//./ })
gid_index=""
for g in /sys/class/infiniband/"$RAIL_A_HCA"/ports/1/gids/*; do
  i=${g##*/}
  if [ "$(cat "$g" 2>/dev/null)" = "$want_gid" ] && \
     [ "$(cat "/sys/class/infiniband/$RAIL_A_HCA/ports/1/gid_attrs/types/$i" 2>/dev/null)" = "RoCE v2" ]; then
    gid_index=$i
    break
  fi
done
[ -n "$gid_index" ] || fail "no RoCE v2 GID for $my_ip on $RAIL_A_HCA"
note "NCCL_IB_GID_INDEX=$gid_index"

# ---- nothing else holds the GPU or would restart something that does
if systemctl is-active --quiet glm53-fleet.service 2>/dev/null; then
  fail "glm53-fleet.service is active: its watchdog relaunches GLM when /health drops (docs/RUNBOOK.md, step 2)"
fi
others=$(docker ps --format '{{.Names}}' | grep -v "^$CONTAINER\$" | grep -E '^(vllm|glm|sglang)' || true)
[ -z "$others" ] || fail "model containers running: $others"
if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  [ "$mode" = run ] && fail "container $CONTAINER exists; cluster.sh down saves its log and removes it"
fi

# ---- image
image_id=$(docker image inspect "$IMAGE" --format '{{.Id}}' 2>/dev/null) || fail "image $IMAGE missing (build/ship-image.sh)"
note "image $IMAGE $image_id"

# ---- patches: rendered, and still the reviewed bytes
patch_dir="$PATCH_ROOT/$PATCH_SET"
[ -f "$patch_dir/mounts.txt" ] || fail "no rendered patch set at $patch_dir (patches/render.sh)"
cmp -s "$patch_dir/SHA256SUMS" "$root/patches/$PATCH_SET/SHA256SUMS" || fail "$patch_dir was rendered from a different patch set revision"
(cd "$patch_dir" && sha256sum --quiet -c SHA256SUMS) || fail "rendered patch files changed on disk"
note "patch set $PATCH_SET ($(wc -l < "$patch_dir/mounts.txt") files, hashes match)"

# ---- model: full shards by size, Engram slice for exactly this rank
python3 "$root/weights/verify.py" "$MODEL_DIR" --size-only >/dev/null || fail "checkpoint incomplete (weights/verify.py $MODEL_DIR)"
python3 - "$MODEL_DIR" "$rank" "$MODEL_REVISION" <<'PY' || fail "Engram slice does not belong to this rank"
import json, os, sys
md, rank, rev = sys.argv[1], int(sys.argv[2]), sys.argv[3]
j = json.load(open(os.path.join(md, "engram-local.json")))
assert (j["rank"], j["tp_size"], j["revision"]) == (rank, 4, rev), (j["rank"], j["tp_size"], j["revision"])
for s in ("model-00047-of-00048.safetensors", "model-00048-of-00048.safetensors"):
    st = os.stat(os.path.join(md, s))
    assert st.st_blocks * 512 > 20 * 2**30, f"{s}: only {st.st_blocks * 512 / 2**30:.1f} GiB allocated"
print("  ok: Engram rows", j["layers"], "for rank", rank)
PY

mkdir -p "$CACHE_DIR"
site=/usr/local/lib/python3.12/dist-packages/vllm
name_model=/models/DeepSeek-V4.1-Flash

mounts=()
while read -r rel; do
  [ -n "$rel" ] && mounts+=(-v "$patch_dir/vllm/$rel:$site/$rel:ro")
done < "$patch_dir/mounts.txt"

K=$SPEC_K
cg_sizes=$( { seq "$K" "$K" $((K * SEQS)); seq $((K + 1)) $((K + 1)) $(((K + 1) * SEQS)); } | sort -n -u | paste -sd, - )

envs=(
  "VLLM_HOST_IP=$my_ip" HF_HOME=/cache/huggingface HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
  "VLLM_CACHE_ROOT=/cache/vllm-${IMAGE##*:}-$PATCH_SET" VLLM_ENGINE_READY_TIMEOUT_S=3600
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True VLLM_USE_RUST_FRONTEND=0
  VLLM_HAS_FLASHINFER_CUBIN=1 TORCH_CUDA_ARCH_LIST=12.1a FLASHINFER_CUDA_ARCH_LIST=12.1a
  FLASHINFER_DISABLE_VERSION_CHECK=1
  DSV41_ENGRAM_DISK=1 DSV41_ENGRAM_DISK_THREADS=32 DSV41_ENGRAM_DISK_CHUNK=16 "DSV41_ENGRAM_DIR=$name_model"
  VLLM_USE_BREAKABLE_CUDAGRAPH=1
  "DSV41_COMPACT_O_PROJ=$COMPACT_O_PROJ" DSV41_SKIP_GRAPH_MEMORY_PROFILE=1 DSV41_CLEAR_STATE_AFTER_CAPTURE=1
  NCCL_NET=IB NCCL_IB_DISABLE=0 "NCCL_IB_HCA=$RAIL_A_HCA" "NCCL_IB_GID_INDEX=$gid_index" "NCCL_IB_TC=$NCCL_IB_TC"
  NCCL_IB_ROCE_VERSION_NUM=2 NCCL_IB_ADDR_FAMILY=AF_INET "NCCL_IB_ADDR_RANGE=$RAIL_A_CIDR"
  "NCCL_SOCKET_IFNAME=$RAIL_A_IFACE" "GLOO_SOCKET_IFNAME=$RAIL_A_IFACE"
  "TP_SOCKET_IFNAME=$RAIL_A_IFACE" "MN_IF_NAME=$RAIL_A_IFACE"
  NCCL_NVLS_ENABLE=0 NCCL_CROSS_NIC=0 NCCL_IB_MERGE_NICS=0 NCCL_CUMEM_ENABLE=0
  NCCL_IGNORE_CPU_AFFINITY=1 NCCL_DEBUG=WARN TORCH_NCCL_ASYNC_ERROR_HANDLING=1
  MAX_JOBS=2 FLASHINFER_NVCC_THREADS=1 VLLM_USE_FLASHINFER_SAMPLER=0
  TILELANG_CACHE_DIR=/cache/tilelang TRITON_CACHE_DIR=/cache/triton
)
# Levers (docs/LEVERS.md): extra "-e K=V" pairs, appended last so they win.
read -r -a lever_envs <<< "${LEVER_ENV:-}"
for e in "${lever_envs[@]}"; do envs+=("$e"); done

args=(run --gpus all -d --name "$CONTAINER" --restart no --network host --ipc host
  --shm-size 32g --memory 112g --memory-swap 112g
  --ulimit memlock=-1:-1 --ulimit nofile=1048576:1048576
  --cap-add IPC_LOCK --device /dev/infiniband:/dev/infiniband --oom-score-adj 500
  --label "dsv41.rank=$rank" --label "dsv41.patch_set=$PATCH_SET" --label "dsv41.gid_index=$gid_index"
  -v "$MODEL_DIR:$name_model:ro" -v "$CACHE_DIR:/cache" "${mounts[@]}")
for e in "${envs[@]}"; do args+=(-e "$e"); done
args+=("$IMAGE" "$name_model" --served-model-name deepseek-v4.1-flash
  --host "$API_HOST" --port "$API_PORT"
  --tensor-parallel-size 4 --gpu-memory-utilization "$GMU"
  --max-model-len "$MAXLEN" --max-num-seqs "$SEQS" --max-num-batched-tokens "$MAX_BATCHED"
  --engram-config '{"cpu_offload":false}' --default-chat-template-kwargs '{"thinking":false}'
  --tool-call-parser deepseek_v41 --enable-auto-tool-choice --reasoning-parser deepseek_v41
  --speculative-config "{\"method\":\"dspark\",\"num_speculative_tokens\":$K,\"draft_sample_method\":\"probabilistic\",\"rejection_sample_method\":\"block\",\"enable_adaptive_verification\":false}"
  --compilation-config "{\"cudagraph_mode\":\"FULL_AND_PIECEWISE\",\"cudagraph_capture_sizes\":[$cg_sizes]}"
  --distributed-executor-backend mp --nnodes 4 --node-rank "$rank"
  --master-addr "${RAIL_A_IPS[0]}" --master-port "$MASTER_PORT"
  --block-size 128 --limit-mm-per-prompt '{"image":4}' --mm-processor-cache-gb 1)
[ "$rank" -eq 0 ] || args+=(--headless)
read -r -a extra <<< "${VLLM_EXTRA:-}"
args+=("${extra[@]}")

case "$mode" in
  --preflight) echo "preflight passed: rank $rank"; exit 0 ;;
  --dry-run) printf '%q ' docker "${args[@]}"; printf '\n'; exit 0 ;;
esac

# One cache drop right before loading, as both upstream launchers do: the load needs the
# unified pool, not yesterday's page cache.
sync -f "$MODEL_DIR"
echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null
avail=$(awk '/MemAvailable:/ {print int($2/1048576)}' /proc/meminfo)
[ "$avail" -ge 100 ] || fail "MemAvailable $avail GiB < 100 GiB after dropping caches"

docker "${args[@]}" >/dev/null
echo "started $CONTAINER rank=$rank gid=$gid_index set=$PATCH_SET k=$K maxlen=$MAXLEN avail=${avail}GiB"
sleep 3
docker ps --format '{{.Names}}' | grep -q "^$CONTAINER\$" || { docker logs --tail 40 "$CONTAINER" >&2; exit 1; }
