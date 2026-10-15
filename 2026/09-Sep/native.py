import array, ctypes as C, pathlib, time
from paths import library
dll = C.CDLL(str(library('checker')))
U = C.c_uint64
I = C.c_uint32
PU = C.POINTER(U)
PI = C.POINTER(I)
dll.make_masks.argtypes = [U, U, C.c_int, C.c_int, C.POINTER(PU), C.POINTER(PI), C.POINTER(PI), PU, PU]
dll.make_masks.restype = C.c_int
dll.check_pairs.argtypes = [PU, U, PU, PI, PI]
dll.check_pairs.restype = C.c_int

def make_masks(M, D, L, limit):
    data = PU()
    ps = PI()
    offsets = PI()
    nt = U()
    np = U()
    assert dll.make_masks(M, D, L, limit, C.byref(data), C.byref(ps), C.byref(offsets), C.byref(nt), C.byref(np)) == 0
    return (list(ps[:np.value]), list(offsets[:np.value]), C.string_at(data, nt.value * 8))

def check_pairs(pairs):
    started = time.perf_counter()
    n = len(pairs)
    inputs = array.array('Q', [v for pair in pairs for v in pair])
    starts = array.array('Q', [0]) * n
    lengths = array.array('I', [0]) * n
    forwards = array.array('I', [0]) * n
    if n:
        inp = (U * (2 * n)).from_buffer(inputs)
        ap = (U * n).from_buffer(starts)
        lp = (I * n).from_buffer(lengths)
        fp = (I * n).from_buffer(forwards)
        assert dll.check_pairs(inp, n, ap, lp, fp) == 0
    text = []
    best = hits = 0
    hist = [0] * 61
    for (orig, d), a, k, fwd in zip(pairs, starts, lengths, forwards):
        hist[fwd] += 1
        if k > best:
            best = k
            text.append(f'RECORD a={a} d={d} length={k} end={a + (k - 1 if k else 0) * d}')
        if k >= 45:
            hits += 1
            text.append(f'VERIFIED a={a} d={d} length={k} end={a + (k - 1) * d}')
    text.append(f'DONE candidates={n} best={best} hits={hits} seconds={time.perf_counter() - started}')
    text.append('HIST' + ''.join((f' {k}:{v}' for k, v in enumerate(hist) if v)))
    return '\n'.join(text) + '\n'
import array, ctypes as C, pathlib
inverse_dll = C.CDLL(str(library('inverse')))
U = C.c_uint64
I = C.c_uint32
inverse_dll.inverses.argtypes = [C.POINTER(U), C.c_size_t, C.POINTER(I), C.c_size_t, C.POINTER(I)]
inverse_dll.inverses.restype = C.c_int

def inverse_bytes(Ds, gps):
    ds = array.array('Q', Ds)
    ps = array.array('I', gps)
    out = array.array('I', [0]) * (len(ds) * len(ps))
    assert ds and ps
    assert inverse_dll.inverses((U * len(ds)).from_buffer(ds), len(ds), (I * len(ps)).from_buffer(ps), len(ps), (I * len(out)).from_buffer(out)) == 0
    return out.tobytes()
