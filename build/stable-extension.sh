#!/usr/bin/env bash
# Runs inside the base image with the vLLM source at /src. Rebuilds only _C_stable_libtorch
# for sm_121a: the DeepSeek-V4.1 kernel changes live in that extension, everything else is
# inherited from the base image.
# From Tech2Wild/Kai's build_stable_ext.sh via 0xTank's stable-extension.sh (tested settings).
set -euo pipefail
export TORCH_CUDA_ARCH_LIST=12.1a
python3 -m pip install 'cmake>=3.26,<4'
cd /src
mkdir -p build/_deps/cutlass-src
if [ ! -f build/_deps/cutlass-src/include/cutlass/cutlass.h ]; then
  curl --fail --location --retry 5 --max-time 900 \
    https://codeload.github.com/NVIDIA/cutlass/tar.gz/refs/tags/v4.7.1 \
    | tar xz -C build/_deps/cutlass-src --strip-components=1
fi
test -f build/_deps/cutlass-src/include/cutlass/cutlass.h
# Stable-only build: skip the external projects (FlashMLA, vllm-flash-attn, ...), which the
# base image already carries and which would multiply build time and memory.
if ! grep -q 'STABLE-ONLY BUILD' CMakeLists.txt; then
  sed -i -E 's|^(\s*)include\(cmake/external_projects/|\1# STABLE-ONLY BUILD: include(cmake/external_projects/|' CMakeLists.txt
fi
PYPATH=$(python3 -c 'import sys; print(":".join(p for p in sys.path if p))')
TORCH_PREFIX=$(python3 -c 'import torch; print(torch.utils.cmake_prefix_path)')
cmake -S /src -B /src/build -G Ninja -DCMAKE_BUILD_TYPE=Release -DVLLM_TARGET_DEVICE=cuda \
  -DVLLM_PYTHON_EXECUTABLE=/usr/bin/python3 -DVLLM_PYTHON_PATH="$PYPATH" \
  -DFETCHCONTENT_BASE_DIR=/src/build/_deps -DFETCHCONTENT_SOURCE_DIR_CUTLASS=/src/build/_deps/cutlass-src \
  -DCMAKE_PREFIX_PATH="$TORCH_PREFIX" -DNVCC_THREADS=1 -DCUDA_nvrtc_LIBRARY=/usr/local/cuda/lib64/libnvrtc.so.13
cmake --build /src/build --target _C_stable_libtorch -j "${JOBS:-4}"
find /src/build -maxdepth 2 -name '_C_stable_libtorch*.so' -exec cp -v {} /src/vllm/ \;
test -f /src/vllm/_C_stable_libtorch.abi3.so
