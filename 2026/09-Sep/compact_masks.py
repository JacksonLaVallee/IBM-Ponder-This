import functools, hashlib, json, math, pathlib, time
import numpy as np
from mask_table import masks as original_masks
from paths import CACHE as w

@functools.lru_cache(1)
def masks(M, g, L, limit=2000):
    t = time.perf_counter()
    ps, offs, rows, raw = original_masks(M, g, L, limit)
    positions = dict(zip(ps, offs))
    words = np.frombuffer(raw, dtype=np.uint64)
    divs = [p for p, nr in zip(ps, rows) if nr == 1]
    groups = []
    group = []
    prod = 1
    for p in divs:
        if group and prod * p > 4096:
            groups.append(group)
            group = []
            prod = 1
        group.append(p)
        prod *= p
    if group:
        groups.append(group)
    newps = []
    newo = []
    newr = []
    parts = []
    offset = len(raw) // 8
    for group in groups:
        q = math.prod(group)
        if len(group) == 1:
            newps.append(q)
            newo.append(positions[q])
            newr.append(1)
            continue
        r = np.arange(q, dtype=np.uint64)
        mask = np.full(q, 2 ** 64 - 1, dtype=np.uint64)
        for p in group:
            mask &= words[positions[p] + r % p]
        good = np.ones(q, dtype=bool)
        for p in group:
            good &= r % p != 0
        assert np.all(mask & 1 == good)
        S = 6 * M % q
        assert np.all(mask[(r + S) % q] == mask >> 1 | good[(r + 64 * S) % q].astype(np.uint64) << 63)
        for a in [0, 1, q // 2, q - 1]:
            expected = sum((int(all(((a + i * 6 * M) % p for p in group))) << i for i in range(64)))
            assert int(mask[a]) == expected
        newps.append(q)
        newo.append(offset)
        newr.append(1)
        parts.append(mask.tobytes())
        offset += q
    for p, o, nr in zip(ps, offs, rows):
        if nr > 1:
            newps.append(p)
            newo.append(o)
            newr.append(nr)
    result = raw + b''.join(parts)
    meta = dict(passed=True, M=M, g=g, L=L, limit=limit, groups=groups, source_sha256=hashlib.sha256(raw).hexdigest(), combined_sha256=hashlib.sha256(b''.join(parts)).hexdigest(), added_bytes=sum(map(len, parts)), seconds=time.perf_counter() - t)
    (w / f'next56-compact-M{M}-G{g}-L{L}-F{limit}.json').write_text(json.dumps(meta, indent=2))
    return (newps, newo, newr, result)
