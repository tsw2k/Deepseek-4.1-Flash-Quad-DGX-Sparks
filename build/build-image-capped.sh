#!/usr/bin/env bash
# Build an image next to a serving rank, inside a hard memory cap, instead of in a window.
#
#   VLLM_PIN=e47aa780bccf59f59dfa2cbb18e17a10b4fe69ba TAG=vllm-dsv41:e47aa780 \
#     bash build/build-image-capped.sh base
#   BASE_TAG=vllm-dsv41:e47aa780 TAG=vllm-dsv41:exl3-e47aa780 \
#     bash build/build-image-capped.sh cuda-exl3
#
# Same chain as build-image.sh (stable extension, overlay, FlashInfer runtime) and the same pins,
# but every heavy step runs in `docker run --memory MEM` and is committed, because BuildKit's
# `docker build` cannot be memory-capped. Within the cap a compile that runs out of memory is
# OOM-killed inside its own cgroup; it cannot take the node's unified memory from the engine.
# Tech2Wild built cuda-exl3 this way (3 GiB, one job) next to a live boot-10 worker.
#
# Slow on purpose: MAX_JOBS=1. No GPU is used, so the runtime kernel check that build-image.sh
# does (verify-runtime.py) is left to the first boot: a serving GB10 does not allow a second
# CUDA context.
#
#   base       vLLM at VLLM_PIN + _C_stable_libtorch for sm_121a + FlashInfer 07869c61 with its
#              SM120 kernels prebuilt (what build-image.sh makes, capped)
#   cuda-exl3  Zeuss5/cuda-exl3 at CUDA_EXL3_PIN compiled for sm_121a on top of BASE_TAG
#              (Tech2Wild's build_exl3a.sh)
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
what=${1:?usage: build-image-capped.sh base|cuda-exl3}
MEM=${MEM:-6g}
JOBS=${JOBS:-1}
WORK=${WORK:-/var/tmp/dsv41-build}
BASE=vllm/vllm-openai:nightly-8a728663c1c3eeace834a95f5654fa653cc1998c
CUDA_EXL3_PIN=${CUDA_EXL3_PIN:-6a1ffc34}
: "${TAG:?set TAG}"
mkdir -p "$WORK"
log="$WORK/capped-$what-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "$log") 2>&1
say() { echo "[$(date -u +%T)] $*"; }
avail() { awk '/MemAvailable:/ {print int($2/1048576)}' /proc/meminfo; }
say "build $what -> $TAG on $(hostname), cap $MEM, jobs $JOBS, MemAvailable $(avail) GiB, log $log"
[ "$(avail)" -ge 10 ] || { say "MemAvailable $(avail) GiB < 10 GiB: not starting even a capped build"; exit 3; }
docker image inspect "$BASE" >/dev/null 2>&1 || { say "base image $BASE missing here; ship it over rail B, do not pull it again"; exit 3; }

# Sample the node's lowest MemAvailable for the log.
( m=999; while sleep 5; do a=$(avail); [ "$a" -lt "$m" ] && m=$a && echo "$m" > "$WORK/capped-min-avail"; done ) &
sampler=$!
trap 'kill $sampler 2>/dev/null || true' EXIT

# docker commit keeps the container's config, including an --entrypoint override: restore the
# base image's entrypoint and cmd explicitly.
commit_as() {  # commit_as CONTAINER FROM_IMAGE TAG [--change ...]
  local c=$1 from=$2 tag=$3; shift 3
  local ep cmd
  ep=$(docker image inspect "$from" --format '{{json .Config.Entrypoint}}')
  cmd=$(docker image inspect "$from" --format '{{json .Config.Cmd}}')
  local ch=(--change "ENTRYPOINT $ep")
  [ "$cmd" = null ] || ch+=(--change "CMD $cmd")
  docker commit "${ch[@]}" "$@" "$c" "$tag" >/dev/null
  docker rm "$c" >/dev/null
  say "committed $tag $(docker image inspect "$tag" --format '{{.Id}}')"
}

run_capped() {  # run_capped NAME IMAGE SCRIPT [docker run args...]
  local name=$1 image=$2 script=$3; shift 3
  docker rm -f "$name" >/dev/null 2>&1 || true
  if ! docker run --name "$name" --memory "$MEM" --memory-swap "$MEM" --entrypoint bash "$@" "$image" -c "$script"; then
    say "step $name failed (OOMKilled=$(docker inspect "$name" --format '{{.State.OOMKilled}}' 2>/dev/null)); raise MEM or check the log"
    exit 4
  fi
}

case "$what" in
base)
  : "${VLLM_PIN:?set VLLM_PIN}"
  short=${VLLM_PIN:0:8}
  src="$WORK/vllm-$short"
  if [ ! -d "$src/.git" ]; then
    git clone --filter=blob:none https://github.com/vllm-project/vllm.git "$src"
  fi
  git -C "$src" fetch --quiet origin "$VLLM_PIN"
  git -C "$src" checkout --quiet --detach "$VLLM_PIN"
  mkdir -p /var/tmp/image-archive
  [ -f "/var/tmp/image-archive/vllm-$VLLM_PIN.tar.gz" ] || \
    git -C "$src" archive --format=tar.gz -o "/var/tmp/image-archive/vllm-$VLLM_PIN.tar.gz" "$VLLM_PIN"

  say "1/3 _C_stable_libtorch for sm_121a"
  run_capped "capped-stable-$short" "$BASE" "JOBS=$JOBS bash /recipe/stable-extension.sh" \
    -v "$src:/src" -v "$here:/recipe:ro"
  docker rm "capped-stable-$short" >/dev/null

  say "2/3 overlay (copy only)"
  cp "$here/overlay.dockerignore" "$src/.dockerignore"
  docker build --progress=plain -f "$here/Dockerfile.overlay" -t "vllm-dsv41:overlay-$short" "$src"

  say "3/3 FlashInfer runtime, kernels prebuilt under the launcher environment"
  run_capped "capped-runtime-$short" "vllm-dsv41:overlay-$short" "
    set -euo pipefail
    pip uninstall -y flashinfer-jit-cache flashinfer-cubin flashinfer-python
    mkdir -p /opt/fi-src/3rdparty/cutlass /opt/fi-src/3rdparty/cccl /opt/fi-src/3rdparty/spdlog
    curl -fL --retry 5 --max-time 900 https://codeload.github.com/flashinfer-ai/flashinfer/tar.gz/07869c61ba581e6d6b8ad8d142f4a6c89b707cc1 | tar xz -C /opt/fi-src --strip-components=1
    curl -fL --retry 5 --max-time 900 https://codeload.github.com/NVIDIA/cutlass/tar.gz/b46b16d003484063bca4ed365e44095c4c6ed633 | tar xz -C /opt/fi-src/3rdparty/cutlass --strip-components=1
    curl -fL --retry 5 --max-time 900 https://codeload.github.com/NVIDIA/cccl/tar.gz/16bd510c9b712e82b0ab6cbb630d8e29ba1f7116 | tar xz -C /opt/fi-src/3rdparty/cccl --strip-components=1
    curl -fL --retry 5 --max-time 900 https://codeload.github.com/gabime/spdlog/tar.gz/c3aed4b68373955e1cc94307683d44dca1515d2b | tar xz -C /opt/fi-src/3rdparty/spdlog --strip-components=1
    cd /opt/fi-src && BUILD_NVEP=0 FLASHINFER_BUILD_NO_PIP=1 MAX_JOBS=$JOBS pip install --no-deps --no-build-isolation . && rm -rf /opt/fi-src/build
    export VLLM_HAS_FLASHINFER_CUBIN=1 FLASHINFER_CUDA_ARCH_LIST=12.1a TORCH_CUDA_ARCH_LIST=12.1a FLASHINFER_DISABLE_VERSION_CHECK=1 FLASHINFER_NVCC_THREADS=1 MAX_JOBS=$JOBS
    python3 -c \"import flashinfer; from flashinfer.mla import supported_sparse_mla_sm120_configs as f; assert f()['dsv4'].supports_decode(num_heads=16, topk=1152); print(flashinfer.__version__)\"
    python3 -c \"from flashinfer.jit.gemm import gen_gemm_sm120_module_cutlass_mxfp8 as gen; s=gen(); b=getattr(s,'build',None); b(verbose=True) if b else s.build_and_load(); print('MXFP8_BUILT')\"
    python3 /recipe/prewarm.py
  " -v "$here:/recipe:ro"
  # Same image ENV as Dockerfile.runtime, so the prebuilt kernels are cache hits at runtime.
  commit_as "capped-runtime-$short" "vllm-dsv41:overlay-$short" "$TAG" \
    --change "ENV VLLM_HAS_FLASHINFER_CUBIN=1" --change "ENV FLASHINFER_CUDA_ARCH_LIST=12.1a" \
    --change "ENV TORCH_CUDA_ARCH_LIST=12.1a" --change "ENV FLASHINFER_DISABLE_VERSION_CHECK=1" \
    --change "ENV FLASHINFER_NVCC_THREADS=1" --change "ENV MAX_JOBS=2" \
    --change "LABEL dsv41.vllm_pin=$VLLM_PIN"
  ;;
cuda-exl3)
  : "${BASE_TAG:?set BASE_TAG}"
  docker image inspect "$BASE_TAG" >/dev/null
  say "cuda-exl3 $CUDA_EXL3_PIN on $BASE_TAG"
  run_capped "capped-exl3" "$BASE_TAG" "
    set -euo pipefail
    mkdir -p /opt/cuda-exl3 && curl -fsSL https://codeload.github.com/Zeuss5/cuda-exl3/tar.gz/$CUDA_EXL3_PIN | tar xz -C /opt/cuda-exl3 --strip-components=1
    cd /opt/cuda-exl3 && TORCH_CUDA_ARCH_LIST=12.1a MAX_JOBS=$JOBS pip install --no-deps --no-build-isolation . 2>&1 | tail -25
    # torch first: cuda_exl3._C links libc10.so, which only torch's import puts on the path
    python3 -c 'import torch, cuda_exl3, cuda_exl3._C; print(\"cuda_exl3 import ok\", cuda_exl3.__file__)'
  "
  commit_as "capped-exl3" "$BASE_TAG" "$TAG" --change "LABEL dsv41.cuda_exl3=$CUDA_EXL3_PIN"
  ;;
*)
  echo "unknown step: $what" >&2; exit 2 ;;
esac
say "done; lowest MemAvailable on the node during the build: $(cat "$WORK/capped-min-avail" 2>/dev/null) GiB"
