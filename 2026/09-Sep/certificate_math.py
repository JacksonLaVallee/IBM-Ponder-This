import csv, json, math, pathlib, random, time

def prime(n):
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        a %= n
        if not a:
            continue
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True

def factor(n):
    assert 0 < n < 2 ** 64
    original = n
    fs = {}
    rng = random.Random(n)

    def add(p):
        fs[p] = fs.get(p, 0) + 1

    def split(v):
        if v == 1:
            return
        if prime(v):
            add(v)
            return
        r = math.isqrt(v)
        if r * r == v:
            split(r)
            split(r)
            return
        while True:
            c = rng.randrange(1, v)
            x = y = rng.randrange(2, v)
            g = 1
            while g == 1:
                x = (x * x + c) % v
                y = (y * y + c) % v
                y = (y * y + c) % v
                g = math.gcd(abs(x - y), v)
            if g != v:
                split(g)
                split(v // g)
                return
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97):
        while n % p == 0:
            add(p)
            n //= p
    split(n)
    assert math.prod((p ** e for p, e in fs.items())) == original
    return sorted(fs.items())

def sqrt_mod(a, p):
    a %= p
    assert pow(a, (p - 1) // 2, p) == 1
    if p % 4 == 3:
        return pow(a, (p + 1) // 4, p)
    q = p - 1
    s = 0
    while q % 2 == 0:
        q //= 2
        s += 1
    z = 2
    while pow(z, (p - 1) // 2, p) != p - 1:
        z += 1
    c = pow(z, q, p)
    x = pow(a, (q + 1) // 2, p)
    t = pow(a, q, p)
    m = s
    while t != 1:
        i = 1
        t2 = t * t % p
        while t2 != 1:
            t2 = t2 * t2 % p
            i += 1
        assert i < m
        b = pow(c, 1 << m - i - 1, p)
        x = x * b % p
        t = t * b * b % p
        c = b * b % p
        m = i
    assert x * x % p == a
    return x

def norm(xy):
    x, y = xy
    return x * x + x * y + y * y

def multiply(a, b):
    x, y = a
    u, v = b
    out = (x * u - y * v, x * v + y * u + y * v)
    assert norm(out) == norm(a) * norm(b)
    return out

def prime_witness(p):
    if p == 3:
        return (1, 1)
    assert p % 3 == 1
    r = sqrt_mod(-3, p)
    a, b = (p, r)
    while b * b > p:
        a, b = (b, a % b)
    u = b
    t = p - u * u
    assert t % 3 == 0
    v = math.isqrt(t // 3)
    assert u * u + 3 * v * v == p
    xy = (u - v, 2 * v)
    assert norm(xy) == p
    return xy

def witness_from_factors(fs):
    xy = (1, 0)
    for p, e in fs:
        if p % 3 == 2:
            assert e % 2 == 0
            xy = multiply(xy, (p ** (e // 2), 0))
        else:
            z = prime_witness(p)
            for _ in range(e):
                xy = multiply(xy, z)
    return xy

def verify(a, d, L, destination):
    t = time.perf_counter()
    rows = []
    for k in range(L):
        n = a + k * d
        fs = factor(n)
        assert all((e % 2 == 0 for p, e in fs if p % 3 == 2))
        x, y = witness_from_factors(fs)
        assert x * x + x * y + y * y == n
        rows.append(dict(index=k, n=n, x=x, y=y, factorization=' * '.join((str(p) if e == 1 else f'{p}^{e}' for p, e in fs))))
    with pathlib.Path(destination).open('w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=rows[0])
        wr.writeheader()
        wr.writerows(rows)
    return dict(a=a, d=d, length=L, end=a + (L - 1) * d, verified=True, seconds=time.perf_counter() - t, method='independent Python factorization, Cornacchia construction, and exact norm identities')
