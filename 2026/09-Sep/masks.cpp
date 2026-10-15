#if defined(_WIN32)
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif
#include <cstdint>
#include <numeric>
#include <vector>
using U=uint64_t;
extern "C" EXPORT int make_universal(U M,U g,int L,int limit,const U** data,const unsigned** ps_out,const unsigned** offsets_out,const unsigned** rows_out,U* nt,U* np){
 try{
  if(limit<100||limit>2000)return 1;
  static std::vector<U> table;static std::vector<unsigned> ps,offsets,rows;table.clear();ps.clear();offsets.clear();rows.clear();std::vector<bool> composite(limit+1);
  for(int p=2;p<=limit;++p){if(composite[p])continue;for(int q=p+p;q<=limit;q+=p)composite[q]=true;if(p<5||p%3!=2||M%p==0)continue;
   U s=6*M%p;if(std::gcd(s,U(p))!=1)return 2;unsigned nr=g%p?p:1;ps.push_back(p);offsets.push_back((unsigned)table.size());rows.push_back(nr);table.resize(table.size()+U(nr)*p);
   for(unsigned dr=0;dr<nr;++dr){std::vector<bool> good(p,true);for(int k=0;k<L;++k)good[(p-(U(k)*dr)%p)%p]=false;
    U word=0;for(int b=0;b<64;++b)word|=U(good[U(b)*s%p])<<b;U r=0,incoming=64*s%p;
    for(int j=0;j<p;++j){table[offsets.back()+U(dr)*p+r]=word;word=(word>>1)|(U(good[incoming])<<63);r+=s;if(r>=U(p))r-=p;incoming+=s;if(incoming>=U(p))incoming-=p;}
   }
  }
  *data=table.data();*ps_out=ps.data();*offsets_out=offsets.data();*rows_out=rows.data();*nt=table.size();*np=ps.size();return 0;
 }catch(...){return 3;}
}
