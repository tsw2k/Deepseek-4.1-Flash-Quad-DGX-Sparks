# Build the SM120 sparse-MLA module under the runtime environment during the image build.
# From Tech2Wild/Kai's prewarm5.py.
import os
import time

for k in ("FLASHINFER_JIT_VERBOSE", "FLASHINFER_JIT_DEBUG", "FLASHINFER_JIT_LINEINFO"):
    os.environ.pop(k, None)  # these switch nvcc to debug/lineinfo flags -> cache miss at runtime

t = time.time()
from flashinfer.mla._sparse_mla_sm120 import get_sparse_mla_sm120_module

try:
    get_sparse_mla_sm120_module()
    print("SPARSE-BUILT+LOADED %.1fs" % (time.time() - t), flush=True)
except Exception as e:  # noqa: BLE001  no GPU during docker build: compiled, load fails
    print("sparse build done, load raised (expected without GPU):", type(e).__name__, str(e)[:160], flush=True)

from flashinfer.jit.gemm import gen_gemm_sm120_module_cutlass_mxfp8

spec = gen_gemm_sm120_module_cutlass_mxfp8()
compiled = spec.is_compiled() if callable(spec.is_compiled) else spec.is_compiled
print("mxfp8 is_compiled under runtime env:", compiled, flush=True)
