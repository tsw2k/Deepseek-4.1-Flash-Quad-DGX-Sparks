#!/usr/bin/env bash
# Build the serving image on ONE GB10 node, then ship it to the others with ship-image.sh.
#
#   bash build/build-image.sh            # on spark-01, with no model loaded anywhere on the node
#
# Nothing in the image is patched: patches are rendered and bind-mounted at launch
# (patches/render.sh), so switching patch sets never rebuilds FlashInfer.
#
# Chain (same steps and pins as 0xTank's measured build, which extends Tech2Wild/Kai's):
#   1. vLLM source at 172d9a17; _C_stable_libtorch rebuilt for sm_121a inside the base image
#   2. overlay: that Python tree copied over the base image's vllm package
#   3. runtime: FlashInfer 07869c61 from source with pinned submodules, SM120 sparse-MLA and
#      MXFP8 GEMM kernels prebuilt under the launcher's exact environment
#   4. checks: kernels load from cache (no runtime JIT) and the GPU sees capability 12.1
#
# Runtime JIT is the reason step 3 exists. In Tech2Wild's boot 3 a FlashInfer compile with 22
# parallel jobs exhausted unified memory on all four nodes at once. MAX_JOBS stays low here
# for the same reason, so this is slow; it is not measured on our nodes yet.
set -euo pipefail

VLLM_PIN=172d9a17117219952fd3d4cdbb04ecb2a09163f4
BASE=vllm/vllm-openai:nightly-8a728663c1c3eeace834a95f5654fa653cc1998c
TAG=${TAG:-vllm-dsv41:172d9a17}
WORK=${WORK:-/var/tmp/dsv41-build}
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
log="$WORK/build-$(date -u +%Y%m%dT%H%M%SZ).log"

avail_gib() { awk '/MemAvailable:/ {print int($2/1048576)}' /proc/meminfo; }

if docker ps --format '{{.Names}}' | grep -qE '^(vllm_|glm53)'; then
  echo "a model container is running on this node; build only with nothing loaded" >&2
  docker ps --format '  {{.Names}} {{.Image}}' >&2
  exit 3
fi
[ "$(avail_gib)" -ge 90 ] || { echo "MemAvailable $(avail_gib) GiB < 90 GiB; refusing to build" >&2; exit 3; }

mkdir -p "$WORK"
exec > >(tee -a "$log") 2>&1
echo "build $TAG on $(hostname) at $(date -u +%FT%TZ), log $log"

# Sample the lowest MemAvailable during the build: the number that says how close a
# compile came to wedging the node.
( m=999; while sleep 2; do a=$(avail_gib); [ "$a" -lt "$m" ] && m=$a && echo "$m" > "$WORK/min-avail"; done ) &
sampler=$!
trap 'kill $sampler 2>/dev/null || true' EXIT

src="$WORK/vllm"
if [ ! -d "$src/.git" ]; then
  git clone --filter=blob:none https://github.com/vllm-project/vllm.git "$src"
fi
git -C "$src" fetch --quiet origin "$VLLM_PIN"
git -C "$src" checkout --quiet --detach "$VLLM_PIN"
git -C "$src" status --porcelain --untracked-files=no | grep -v '^ M CMakeLists.txt$' && {
  echo "$src has local modifications besides the stable-only CMakeLists edit" >&2; exit 4; } || true
# The pin is reachable on GitHub by sha only (no branch points at it) and can be
# garbage-collected there: keep the exact source next to the image.
mkdir -p /var/tmp/image-archive
[ -f "/var/tmp/image-archive/vllm-$VLLM_PIN.tar.gz" ] || \
  git -C "$src" archive --format=tar.gz -o "/var/tmp/image-archive/vllm-$VLLM_PIN.tar.gz" "$VLLM_PIN"

docker pull "$BASE"
docker image inspect "$BASE" --format 'base {{index .RepoDigests 0}}'

docker run --rm --gpus all --ipc host --entrypoint bash \
  -v "$src:/src" -v "$here:/recipe:ro" "$BASE" /recipe/stable-extension.sh

cp "$here/overlay.dockerignore" "$src/.dockerignore"
docker build --progress=plain -f "$here/Dockerfile.overlay" -t vllm-dsv41:overlay "$src"
docker build --progress=plain -f "$here/Dockerfile.runtime" -t "$TAG" "$here"

docker run --rm --gpus all --entrypoint python3 -v "$here:/checks:ro" \
  -e FLASHINFER_CUDA_ARCH_LIST=12.1a -e TORCH_CUDA_ARCH_LIST=12.1a \
  -e FLASHINFER_DISABLE_VERSION_CHECK=1 -e VLLM_HAS_FLASHINFER_CUBIN=1 \
  -e MAX_JOBS=2 -e FLASHINFER_NVCC_THREADS=1 \
  "$TAG" /checks/verify-runtime.py

id=$(docker image inspect "$TAG" --format '{{.Id}}')
echo "$TAG $id" | tee "$WORK/image-id"
echo "done $(date -u +%FT%TZ); lowest MemAvailable during build: $(cat "$WORK/min-avail" 2>/dev/null) GiB"
