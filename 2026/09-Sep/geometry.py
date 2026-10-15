import math
PS = [23, 29, 41, 47, 53, 59, 71, 83, 89, 101, 107, 113, 131, 137]

def geometry(K, mask, L=51):
    assert mask in (31, 63) and L == 51 and (K >= 7)
    square = mask == 31
    g = 5610 * math.prod(PS[:5 + (not square)])
    nond = PS[5 if square else 6:K]
    qs = [3481 if square and p == 59 else p for p in nond]
    residues = []
    for j, p in enumerate(nond):
        if square and p == 59:
            residues.append([-k % 3481 for k in list(range(0, 49, 6)) + [50]])
        elif not square and j == 0:
            residues.append([7, 14])
        else:
            residues.append(list(range(7, p - 56)))
    M = math.prod(qs)
    rad = list(map(len, residues))
    offs = []
    contrib = []
    for q, rr in zip(qs, residues):
        b = M // q
        iv = pow(b, -1, q)
        offs.append(len(contrib))
        contrib.extend((b * (r * iv % q) for r in rr))
    return (g, M, math.prod(rad), rad, offs, contrib)
