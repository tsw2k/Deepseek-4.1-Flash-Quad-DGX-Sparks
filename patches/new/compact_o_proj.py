"""Opt-in compact MXFP8 output projection; BF16 fallback remains available."""
import torch
import triton
import triton.language as tl
from vllm.utils.torch_utils import direct_register_custom_op

@triton.jit
def _partial(X,W,WS,T,M:tl.constexpr,G:tl.constexpr,N:tl.constexpr,K:tl.constexpr,
             XS0:tl.constexpr,XS1:tl.constexpr,S:tl.constexpr=8,BN:tl.constexpr=8):
    ni=tl.program_id(0)*BN+tl.arange(0,BN)
    g=tl.program_id(1)
    s=tl.program_id(2)
    ki=s*(K//S)+tl.arange(0,K//S)
    b=tl.load(W+g*N*K+ni[:,None]*K+ki[None,:],ni[:,None]<N,other=0.0)
    scale=tl.load(WS+g*N*(K//32)+ni[:,None]*(K//32)+ki[None,:]//32,
                  ni[:,None]<N,other=127).to(tl.int32)
    factor=(scale << 23).to(tl.float32,bitcast=True)
    b=(b.to(tl.float32)*factor).to(tl.bfloat16).to(tl.float32)
    for mi in tl.static_range(M):
        a=tl.load(X+mi*XS0+g*XS1+ki).to(tl.float32)
        acc=tl.sum(b*a[None,:],axis=1)
        tl.store(T+s*M*G*N+mi*G*N+g*N+ni,acc,ni<N)

@triton.jit
def _finish(T,O,TOTAL:tl.constexpr,S:tl.constexpr=8):
    ids=tl.program_id(0)*256+tl.arange(0,256)
    acc=tl.full((256,),0,tl.float32)
    for s in tl.static_range(S):
        acc+=tl.load(T+s*TOTAL+ids,ids<TOTAL,other=0.0)
    tl.store(O+ids,acc,ids<TOTAL)

def _compact_bmm(x:torch.Tensor,weight:torch.Tensor,scale:torch.Tensor,
                 fallback_weight:torch.Tensor,out:torch.Tensor)->None:
    m,g,k=x.shape
    n=out.shape[-1]
    supported=(0<m<=8 and k==4096 and n==1024 and g==2
               and x.dtype==torch.bfloat16 and x.stride(2)==1
               and weight.dtype==torch.float8_e4m3fn
               and weight.is_contiguous() and scale.is_contiguous()
               and out.is_contiguous() and out.dtype==torch.bfloat16)
    if not supported:
        torch.bmm(x.transpose(0,1),fallback_weight.view(g,n,k).transpose(1,2),
                  out=out.transpose(0,1))
        return
    tmp=torch.empty((8,m,g,n),device=x.device,dtype=torch.float32)
    _partial[(triton.cdiv(n,8),g,8)](x,weight,scale.view(torch.uint8),tmp,
        M=m,G=g,N=n,K=k,XS0=x.stride(0),XS1=x.stride(1),num_warps=8)
    _finish[(triton.cdiv(m*g*n,256),)](tmp,out,TOTAL=m*g*n)

def _fake(x:torch.Tensor,weight:torch.Tensor,scale:torch.Tensor,
          fallback_weight:torch.Tensor,out:torch.Tensor)->None:
    return None

direct_register_custom_op('dsv41_compact_o_bmm',_compact_bmm,
                          mutates_args=['out'],fake_impl=_fake)
