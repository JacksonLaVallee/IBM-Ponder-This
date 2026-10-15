import ctypes as C, functools, hashlib, json, pathlib, time, math
import numpy as np
from paths import CACHE as w, library
U = C.c_uint64
I = C.c_uint
PU = C.POINTER(U)
PI = C.POINTER(I)

@functools.lru_cache(1)
def masks(M, g, L, limit=2000):
    tag = w / f'next56-universal-M{M}-G{g}-L{L}-F{limit}'
    meta = tag.with_suffix('.json')
    binary = tag.with_suffix('.bin')
    if meta.exists() and binary.exists():
        v = json.loads(meta.read_text())
        raw = binary.read_bytes()
        assert v['passed'] and hashlib.sha256(raw).hexdigest() == v['sha256']
        return (v['primes'], v['offsets'], v['rows'], raw)
    t = time.perf_counter()
    dll = C.CDLL(str(library('masks')))
    dll.make_universal.argtypes = [U, U, C.c_int, C.c_int, C.POINTER(PU), C.POINTER(PI), C.POINTER(PI), C.POINTER(PI), PU, PU]
    dll.make_universal.restype = C.c_int
    data = PU()
    ps = PI()
    offs = PI()
    rows = PI()
    nt = U()
    nf = U()
    assert dll.make_universal(M, g, L, limit, C.byref(data), C.byref(ps), C.byref(offs), C.byref(rows), C.byref(nt), C.byref(nf)) == 0
    raw = C.string_at(data, nt.value * 8)
    ps = list(ps[:nf.value])
    offs = list(offs[:nf.value])
    rows = list(rows[:nf.value])
    generation = time.perf_counter() - t
    t = time.perf_counter()
    words = np.frombuffer(raw, dtype=np.uint64)
    entries = 0
    for p, off, nr in zip(ps, offs, rows):
        r = np.arange(p, dtype=np.uint64)
        S = 6 * M % p
        mat = words[off:off + nr * p].reshape(nr, p)
        if nr == 1:
            good = r[None, :] != 0
        else:
            inv = np.array([0] + [pow(d, -1, p) for d in range(1, p)], dtype=np.uint64)
            good = (p - r[None, :]) * inv[:, None] % p >= L
            good[0, :] = r != 0
        assert np.all(mat & 1 == good)
        expected = mat >> 1 | good[:, (r + 64 * S) % p].astype(np.uint64) << 63
        assert np.all(mat[:, (r + S) % p] == expected)
        entries += nr * p
    assert entries == nt.value
    v = dict(passed=True, M=M, g=g, L=L, limit=limit, primes=ps, offsets=offs, rows=rows, entries=entries, bytes=len(raw), generation_seconds=generation, validation_seconds=time.perf_counter() - t, all_words_checked=True, sha256=hashlib.sha256(raw).hexdigest(), dll_sha256=hashlib.sha256(library('masks').read_bytes()).hexdigest())
    binary.write_bytes(raw)
    meta.write_text(json.dumps(v, indent=2))
    return (ps, offs, rows, raw)
