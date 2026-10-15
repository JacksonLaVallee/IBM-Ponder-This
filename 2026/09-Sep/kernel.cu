#define PACK 8
typedef unsigned long long U;
__device__ unsigned rem64(U n,unsigned p,U reciprocal){unsigned q=(unsigned)__umul64hi(n,reciprocal),r=(unsigned)n-q*p;return r>=p?r-p:r;}
#define ARGS const U* amin_all,const U* amax_all,const U* Ds,U M,U montinv,const U* gRs,U start,unsigned count,const U* saved_roots,int nr,const unsigned* radices,const unsigned* roff,const U* contribution,int nf,const unsigned* primes,const U* rec,const unsigned* offsets_all,const U* masks,const unsigned* deltas,unsigned L,unsigned E,int gn,const unsigned* gp,const unsigned* gi_all,const U* gr,U* stats,U* output,U capacity,U* survivors,unsigned* survivor_counts,unsigned survivor_capacity,int split_at,U* survivors2,unsigned* survivor_counts2,int split_second
extern "C" __global__ void search(ARGS){
 unsigned tid=blockIdx.x*blockDim.x+threadIdx.x;unsigned active=__ballot_sync(0xffffffffU,tid<count);if(tid>=count)return;unsigned plane=blockIdx.y;U amin=amin_all[plane],amax=amax_all[plane];U D=Ds[plane],gR=gRs[plane];const unsigned* offsets=offsets_all+plane*nf;const unsigned* gi=gi_all+plane*gn;U c=saved_roots[tid];
 U low=c*gR,high=__umul64hi(c,gR),u0=low*montinv;U b=high+__umul64hi(u0,M)+(low!=0);if(b>=M)b-=M;
 U step=6*M,a=b+((7-b%6)*(M%6)%6)*M;if(a<amin)a+=((amin-a+step-1)/step)*step;if(c==~0ULL)a=amax+1;
 U points=0,words=0,checks=0,errors=0,gapchecks=0;

 for(;a<=amax;a+=PACK*64*step){unsigned n=(unsigned)min((U)(PACK*64),(amax-a)/step+1);U bits[PACK];points+=n;words+=(n+63)/64;
  #pragma unroll
  for(int q=0;q<PACK;++q){unsigned nn=n>q*64?min(64U,n-q*64):0;bits[q]=nn==64?~0ULL:(1ULL<<nn)-1;}
  U alive=1;
  for(int j=0;j<split_at&&alive;++j){unsigned p=primes[j],r=(unsigned)rem64(a,p,rec[j]),delta=deltas[j];alive=0;
   #pragma unroll
   for(int q=0;q<PACK;++q){if(bits[q]){bits[q]&=masks[offsets[j]+r];}alive|=bits[q];r+=delta;if(r>=p)r-=p;}
  }
  #pragma unroll
  for(int q=0;q<PACK;++q)if(bits[q]){
    unsigned slot=atomicAdd(survivor_counts+plane,1U);
    if(slot<survivor_capacity){U at=2*(U(plane)*survivor_capacity+slot);survivors[at]=a+q*64*step;survivors[at+1]=bits[q];}
    else ++errors;
  }

 }
 if(errors)atomicAdd(stats+4,errors);unsigned lane=threadIdx.x&31;
 for(int offset=16;offset;offset>>=1){U v0=__shfl_down_sync(active,points,offset),v1=__shfl_down_sync(active,words,offset),v2=__shfl_down_sync(active,checks,offset),v3=__shfl_down_sync(active,gapchecks,offset);if(lane+offset<32&&((active>>(lane+offset))&1)){points+=v0;words+=v1;checks+=v2;gapchecks+=v3;}}
 if(!lane){atomicAdd(stats,points);atomicAdd(stats+1,words);atomicAdd(stats+2,checks);atomicAdd(stats+5,(U)__popc(active));atomicAdd(stats+6,gapchecks);}
}

extern "C" __global__ void middle(ARGS){
 unsigned plane=blockIdx.y,tid=blockIdx.x*blockDim.x+threadIdx.x;
 unsigned active=__ballot_sync(0xffffffffU,tid<survivor_counts[plane]);if(tid>=survivor_counts[plane])return;
 U at=2*(U(plane)*survivor_capacity+tid),a=survivors[at],bits=survivors[at+1],checks=0,errors=0;
 const unsigned* offsets=offsets_all+plane*nf;
 for(int j=split_at;j<split_second&&bits;++j){unsigned r=rem64(a,primes[j],rec[j]);bits&=masks[offsets[j]+r];}
 if(bits){unsigned slot=atomicAdd(survivor_counts2+plane,1U);if(slot<survivor_capacity){U dest=2*(U(plane)*survivor_capacity+slot);survivors2[dest]=a;survivors2[dest+1]=bits;}else ++errors;}
 if(errors)atomicAdd(stats+4,errors);unsigned lane=threadIdx.x&31;
 for(int offset=16;offset;offset>>=1){U x=__shfl_down_sync(active,checks,offset);if(lane+offset<32&&((active>>(lane+offset))&1))checks+=x;}
 if(!lane)atomicAdd(stats+2,checks);
}

extern "C" __global__ void finish(ARGS){
 unsigned plane=blockIdx.y,tid=blockIdx.x*blockDim.x+threadIdx.x;
 unsigned active=__ballot_sync(0xffffffffU,tid<survivor_counts2[plane]);if(tid>=survivor_counts2[plane])return;
 U at=2*(U(plane)*survivor_capacity+tid),a=survivors2[at],bits=survivors2[at+1],D=Ds[plane],step=6*M,checks=0,gapchecks=0,errors=0;
 const unsigned* offsets=offsets_all+plane*nf;const unsigned* gi=gi_all+plane*gn;
 for(int j=split_second;j<nf&&bits;++j){unsigned r=rem64(a,primes[j],rec[j]);bits&=masks[offsets[j]+r];}
 while(bits){unsigned bit=__ffsll((long long)bits)-1;bits&=bits-1;U aa=a+bit*step;unsigned left=min(U(E),(aa-1)/D),right=E;bool good=true;
  for(int j=0;j<gn;++j){unsigned p=gp[j],r=rem64(aa,p,gr[j]),iv=gi[j];
   if(!iv){if(!r){good=false;break;}continue;}unsigned k=rem64(U(p-r)*iv,p,gr[j]);
   if(k<L){good=false;break;}if(k<L+E)right=min(right,k-L);if(k>=p-E)left=min(left,p-k-1);if(left+right<E){good=false;break;}
  }
  if(good){U slot=atomicAdd(stats+3,1ULL);if(slot<capacity){output[2*slot]=aa;output[2*slot+1]=D;}else ++errors;}
 }
 if(errors)atomicAdd(stats+4,errors);unsigned lane=threadIdx.x&31;
 for(int offset=16;offset;offset>>=1){U x=__shfl_down_sync(active,checks,offset),y=__shfl_down_sync(active,gapchecks,offset);if(lane+offset<32&&((active>>(lane+offset))&1)){checks+=x;gapchecks+=y;}}
 if(!lane){atomicAdd(stats+2,checks);atomicAdd(stats+6,gapchecks);}
}

extern "C" __global__ void decode(U start,unsigned count,int nr,const unsigned* radices,const unsigned* roff,const U* contribution,U M,U* output_roots){
 unsigned tid=blockIdx.x*blockDim.x+threadIdx.x;if(tid>=count)return;U c=0;unsigned left=6,right=6;
 if(start+tid<=0xffffffffULL){unsigned r=(unsigned)(start+tid);for(int j=nr-1;j>=0;--j){unsigned digit=r%radices[j];r/=radices[j];U v=contribution[roff[j]+digit];left=min(left,(unsigned)((v>>56)&7));right=min(right,(unsigned)((v>>59)&7));if(left+right<6){c=~0ULL;break;}c+=v&0x00ffffffffffffffULL;if(c>=M)c-=M;}}
 else{U r=start+tid;for(int j=nr-1;j>=0;--j){unsigned digit=(unsigned)(r%radices[j]);r/=radices[j];U v=contribution[roff[j]+digit];left=min(left,(unsigned)((v>>56)&7));right=min(right,(unsigned)((v>>59)&7));if(left+right<6){c=~0ULL;break;}c+=v&0x00ffffffffffffffULL;if(c>=M)c-=M;}}
 output_roots[tid]=c;
}
