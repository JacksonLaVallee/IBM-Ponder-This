import functools

@functools.lru_cache(None)
def primes(lo, hi):
    composite = bytearray(hi + 1)
    out = []
    for p in range(2, hi + 1):
        if composite[p]:
            continue
        composite[p * p::p] = b'\x01' * max(0, (hi - p * p) // p + 1)
        if p > lo and p % 3 == 2:
            out.append(p)
    return out
