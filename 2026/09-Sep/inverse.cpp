#if defined(_WIN32)
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif
#include <cstdint>
#include <cstddef>
extern "C" EXPORT int inverses(const uint64_t* steps, size_t ns, const uint32_t* primes, size_t np, uint32_t* output) {
    for (size_t i=0;i<ns;++i) for (size_t j=0;j<np;++j) {
        const uint32_t p=primes[j]; if(p<2)return 1;
        const uint32_t residue=static_cast<uint32_t>(steps[i]%p);
        if(!residue) { output[i*np+j]=0; continue; }
        int64_t a=p,b=residue,x=0,y=1;
        while(b) { int64_t q=a/b, r=a-q*b,z=x-q*y; a=b;b=r;x=y;y=z; }
        if(a!=1)return 2;
        x%=p;if(x<0)x+=p;
        output[i*np+j]=static_cast<uint32_t>(x);
    }
    return 0;
}
