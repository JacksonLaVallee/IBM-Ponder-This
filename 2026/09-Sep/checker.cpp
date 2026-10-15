#if defined(_WIN32)
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif
#include "factor.h"
#include <algorithm>
#include <cstdint>
#include <numeric>
#include <unordered_map>
#include <vector>
using U=uint64_t;
extern "C" EXPORT int make_masks(U M,U D,int L,int limit,const U** data,const unsigned** ps_out,const unsigned** offsets_out,U* nt,U* np){
 try{
  if(limit<100||limit>20000)return 1;
  static std::vector<U> table;static std::vector<unsigned> ps,offsets;table.clear();ps.clear();offsets.clear();std::vector<bool> composite(limit+1);
  for(int p=2;p<=limit;++p){if(composite[p])continue;for(int q=p+p;q<=limit;q+=p)composite[q]=true;if(p<5||p%3!=2||M%p==0)continue;
   U s=6*M%p;if(std::gcd(s,U(p))!=1)return 2;ps.push_back(p);offsets.push_back((unsigned)table.size());table.resize(table.size()+p);std::vector<bool> good(p,true);
   for(int k=0;k<L;++k)good[(p-(U(k)*(D%p))%p)%p]=false;
   U word=0;for(int b=0;b<64;++b)word|=U(good[U(b)*s%p])<<b;U r=0,incoming=64*s%p;
   for(int j=0;j<p;++j){table[offsets.back()+r]=word;word=(word>>1)|(U(good[incoming])<<63);r+=s;if(r>=U(p))r-=p;incoming+=s;if(incoming>=U(p))incoming-=p;}
  }
  *data=table.data();*ps_out=ps.data();*offsets_out=offsets.data();*nt=table.size();*np=ps.size();return 0;
 }catch(...){return 3;}
}
extern "C" EXPORT int check_pairs(const U* input,U count,U* starts,unsigned* lengths,unsigned* forwards){
 try{
  std::unordered_map<U,bool> memo;
  auto good=[&](U n){auto it=memo.find(n);if(it!=memo.end())return it->second;bool v=loesch_fast(n);memo.emplace(n,v);return v;};
  for(U i=0;i<count;++i){U a=input[2*i],d=input[2*i+1];unsigned k=0;for(;k<60;++k)if(!good(a+k*d))break;forwards[i]=k;if(k)while(a>d&&good(a-d)){a-=d;++k;}starts[i]=a;lengths[i]=k;}
  return 0;
 }catch(...){return 1;}
}
