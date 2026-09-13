# Run inside the built image with a GPU. Fails if a kernel would compile at serving time.
# Combines Tech2Wild/Kai's verify5.py and 0xTank's dsv41-verify-runtime.py.
import importlib
import time

import torch
import vllm
from flashinfer.jit.gemm import gen_gemm_sm120_module_cutlass_mxfp8
from flashinfer.mla._sparse_mla_sm120 import get_sparse_mla_sm120_module

assert torch.cuda.is_available(), "GPU unavailable"
cap = torch.cuda.get_device_capability()
assert cap == (12, 1), f"expected GB10 capability (12, 1), got {cap}"
importlib.import_module("vllm._C_stable_libtorch")

gemm = gen_gemm_sm120_module_cutlass_mxfp8()
compiled = gemm.is_compiled() if callable(gemm.is_compiled) else gemm.is_compiled
assert compiled, "MXFP8 GEMM artifact missing: it would JIT at serving time"
# try_load only checks AOT artifacts at this FlashInfer revision; JIT artifacts go
# through ninja's freshness check, which is instant when the cache is valid.
t = time.monotonic()
gemm.build_and_load()
gemm_s = time.monotonic() - t

t = time.monotonic()
get_sparse_mla_sm120_module()
sparse_s = time.monotonic() - t
# A cache hit loads in seconds; a rebuild takes many minutes.
assert sparse_s < 60, f"sparse_mla_sm120 took {sparse_s:.0f}s: it compiled instead of loading"

print(f"RUNTIME_VERIFIED vllm={vllm.__version__} mxfp8_load={gemm_s:.1f}s sparse_load={sparse_s:.1f}s", flush=True)
