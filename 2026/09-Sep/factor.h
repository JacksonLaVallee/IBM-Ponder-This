#pragma once
#include <cstdint>
#include <cmath>
#include <numeric>
#include <algorithm>
#if defined(_MSC_VER)
#include <intrin.h>
#endif
using u64=uint64_t;
#if defined(_MSC_VER)
inline u64 mmul(u64 a,u64 b,u64 n){if(!a||b<=UINT64_MAX/a)return a*b%n;u64 hi,lo=_umul128(a,b,&hi),rem;_udiv128(hi,lo,n,&rem);return rem;}
#else
inline u64 mmul(u64 a,u64 b,u64 n){return static_cast<unsigned __int128>(a)*b%n;}
#endif
inline u64 mpow(u64 a,u64 d,u64 n){u64 r=1;for(;d;d>>=1,a=mmul(a,a,n))if(d&1)r=mmul(r,a,n);return r;}
inline bool prime64(u64 n){
 if(n<2)return false;
 for(u64 p:{2,3,5,7,11,13,17,19,23,29,31,37})if(n%p==0)return n==p;
 u64 d=n-1,s=0;while(!(d&1)){d>>=1;++s;}
 for(u64 a:{2ULL,325ULL,9375ULL,28178ULL,450775ULL,9780504ULL,1795265022ULL}){
  if(a%n==0)continue;u64 x=mpow(a%n,d,n);if(x==1||x==n-1)continue;bool pass=false;
  for(u64 j=1;j<s;++j){x=mmul(x,x,n);if(x==n-1){pass=true;break;}}if(!pass)return false;
 }return true;
}
inline u64 random64(){static u64 state=20260907;state^=state<<13;state^=state>>7;state^=state<<17;return state;}
inline u64 rho(u64 n){
 if(n%2==0)return 2;if(n%3==0)return 3;
 for(;;){u64 y=2+random64()%(n-3),c=1+random64()%(n-1),g=1,r=1,x=0,ys=0;
  auto f=[&](u64 z){u64 v=mmul(z,z,n);return v>=n-c?v-(n-c):v+c;};
  while(g==1&&r<(1ULL<<20)){
   x=y;for(u64 i=0;i<r;++i)y=f(y);
   for(u64 k=0;k<r&&g==1;k+=64){ys=y;u64 q=1;for(u64 i=0;i<std::min<u64>(64,r-k);++i){y=f(y);q=mmul(q,x>y?x-y:y-x,n);}g=std::gcd(q,n);}r*=2;
  }
  if(g==n)do{ys=f(ys);g=std::gcd(x>ys?x-ys:ys-x,n);}while(g==1);
  if(g>1&&g<n)return g;
 }
}
inline u64 one_prime_factor(u64 n){if(prime64(n))return n;return one_prime_factor(rho(n));}
inline bool square64(u64 n){u64 r=u64(std::sqrt(double(n)));while(r&&r>n/r)--r;while(r+1<=n/(r+1))++r;return r*r==n;}
inline bool loesch_fast(u64 n){
 if(n<2)return true;if(n%3==2)return false;
 for(u64 p:{2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97}){
  if(n%p)continue;int e=0;do{n/=p;++e;}while(n%p==0);if(p%3==2&&(e&1))return false;
 }
 while(n>1){if(square64(n))return true;if(prime64(n))return n%3!=2;u64 p=one_prime_factor(rho(n));int e=0;do{n/=p;++e;}while(n%p==0);if(p%3==2&&(e&1))return false;}
 return true;
}
