from native import inverse_bytes
import array, ctypes as C, importlib, math, time
from gpu import GPU, U, I, W, buf
from gpu import checked, P
from compact_masks import masks as original_masks

def masks(M, g, L, limit=2000):
    ps, offs, rows, raw = original_masks(M, g, L, limit)

    def score(item):
        p, off, nr = item
        if nr > 1:
            return math.log((p - L) / p)
        remaining = p
        prime = 2
        fraction = 1.0
        while prime * prime <= remaining:
            if remaining % prime == 0:
                fraction *= 1 - 1 / prime
                while remaining % prime == 0:
                    remaining //= prime
            prime += 1
        if remaining > 1:
            fraction *= 1 - 1 / remaining
        return math.log(fraction) / 1.0
    ordered = sorted(zip(ps, offs, rows), key=score)
    assert set(ordered) == set(zip(ps, offs, rows))
    return ([v[0] for v in ordered], [v[1] for v in ordered], [v[2] for v in ordered], raw)
from primes import primes
_cache = {}

def uninitialized(gpu, size):
    ptr = U()
    checked(gpu.cu.cuMemAlloc_v2(C.byref(ptr), C.c_size_t(size)), 'allocate scratch')
    gpu.allocations.append(ptr)
    return ptr

def gpu_chunk(gpu, N, lower, K, mask, start, limit, cap, lowspan=0, step_multipliers=(1,), combine_to=-1, block_length=51, filter_limit=10000, pack_size=4, dense_limit=2000, geometry_module='geometry', gap_floor=None, maximum_threads=67108864, step_lower_bounds=None, step_upper_bounds=None, split_at=20, split_second=80):
    global _cache
    t = time.perf_counter()
    geom = importlib.import_module(geometry_module).geometry
    g, M, total, rad, roff, contrib = geom(K, mask, L=block_length)
    assert geometry_module == 'geometry' and block_length == 51 and (M < 2 ** 56)
    from geometry import PS
    nond = [p for j, p in enumerate(PS[:K]) if not mask >> j & 1]
    anchors = sorted(range(nond[0] - 57, 0, -7))
    encoded = []
    for j, p in enumerate(nond):
        residues = anchors if j == 0 else range(7, p - 56)
        for k, r in enumerate(residues):
            left = min(6, r - 1)
            right = min(6, p - r - block_length)
            assert 0 <= left <= 6 and 0 <= right <= 6
            encoded.append(contrib[roff[j] + k] | left << 56 | right << 59)
    assert len(encoded) == len(contrib)
    contrib = encoded
    ms = tuple(step_multipliers)
    Ds = [g * m for m in ms]
    los = tuple([lower] * len(ms) if step_lower_bounds is None else step_lower_bounds)
    his = tuple([N] * len(ms) if step_upper_bounds is None else step_upper_bounds)
    assert len(los) == len(his) == len(ms) and all((0 <= lo < hi <= N for lo, hi in zip(los, his)))
    assert 0 <= start <= limit < total and ms and (len(ms) <= 256) and all((m > 0 and math.gcd(m, M) == 1 for m in ms))
    assert all((hi + 60 * D < 2 ** 63 for hi, D in zip(his, Ds))) and N + 4 * 384 * M < 2 ** 63
    floor = 113 - block_length if gap_floor is None else gap_floor
    max_words = max(((hi - lo + 384 * M - 1) // (384 * M) for lo, hi in zip(los, his)))
    assert max_words >= 1
    input_threads = max(len(ms) * 256, maximum_threads // max_words)
    root_capacity = max(256, input_threads // len(ms))
    survivor_capacity = root_capacity * max_words
    key = (geometry_module, K, mask, M, g, block_length, dense_limit, filter_limit, floor, maximum_threads, root_capacity, max_words)
    if _cache.get('gpu') is not gpu or _cache.get('key') != key:
        gpu.close()
        ps, offs, rows, raw = masks(M, g, block_length, dense_limit)
        gps = primes(floor, filter_limit)
        ptrs = [gpu.put(buf('I', rad)), gpu.put(buf('I', roff)), gpu.put(buf('Q', contrib)), gpu.put(buf('I', ps)), gpu.put(buf('Q', [(1 << 64) // p for p in ps])), gpu.put(raw), gpu.put(buf('I', [384 * M % p for p in ps])), gpu.put(buf('I', gps)), gpu.put(buf('Q', [(1 << 64) // p for p in gps]))]
        decoder = P()
        checked(gpu.cu.cuModuleGetFunction(C.byref(decoder), gpu.module, b'decode'), 'decode function')
        finisher = P()
        checked(gpu.cu.cuModuleGetFunction(C.byref(finisher), gpu.module, b'finish'), 'finish function')
        middle = P()
        checked(gpu.cu.cuModuleGetFunction(C.byref(middle), gpu.module, b'middle'), 'middle function')
        _cache = dict(middle=middle, finisher=finisher, decoder=decoder, gpu=gpu, key=key, ps=ps, offs=offs, rows=rows, gps=gps, ptrs=ptrs, static=len(gpu.allocations), ms=None)
    ps, offs, rows, gps = [_cache[k] for k in ['ps', 'offs', 'rows', 'gps']]
    if _cache['ms'] != ms or _cache.get('bounds') != (los, his):
        for p in gpu.allocations[_cache['static']:]:
            checked(gpu.cu.cuMemFree_v2(p), 'free dynamic')
        gpu.allocations = gpu.allocations[:_cache['static']]
        dyn = [gpu.put(buf('Q', Ds)), gpu.put(buf('Q', [D * (1 << 64) % M for D in Ds])), gpu.put(buf('I', [off + D % p * p if nr > 1 else off for D in Ds for p, off, nr in zip(ps, offs, rows)])), gpu.put(inverse_bytes(Ds, gps)), gpu.put(bytes(56)), gpu.put(bytes(16 * 262144)), gpu.put(buf('Q', [lo + 1 for lo in los])), gpu.put(buf('Q', his)), gpu.put(bytes(8 * root_capacity))]
        dyn.extend([uninitialized(gpu, 16 * survivor_capacity * len(ms)), gpu.put(bytes(4 * len(ms))), uninitialized(gpu, 16 * survivor_capacity * len(ms)), gpu.put(bytes(4 * len(ms)))])
        _cache.update(ms=ms, bounds=(los, his), dyn=dyn)
    rp, op, cp, pp, rec, tab, deltas, gpp, grp = _cache['ptrs']
    dsp, grpDs, offp, gip, stats, output, lowp, highp, rootsbuf, survivors, survivor_counts, survivors2, survivor_counts2 = _cache['dyn']
    assert 0 < split_at < split_second < len(ps) and all((1 < p < 2 ** 31 for p in ps + gps))
    checked(gpu.cu.cuMemsetD8_v2(stats, C.c_ubyte(0), C.c_size_t(56)), 'zero counters')
    setup = time.perf_counter() - t
    t = time.perf_counter()
    done = 0
    batch = 256
    maximum = 0
    launch_seconds = 0.0
    counter_seconds = 0.0
    launches = 0
    staged_words = 0
    stage1_seconds = 0.0
    stage2_seconds = 0.0
    stage3_seconds = 0.0
    second_staged_words = 0
    compact_download_seconds = 0.0
    while start + done <= limit:
        count = min(batch, limit + 1 - start - done)
        argv = [lowp, highp, dsp, U(M), U(-pow(M, -1, 1 << 64) % (1 << 64)), grpDs, U(start + done), C.c_uint(count), rootsbuf, I(len(rad)), rp, op, cp, I(len(ps)), pp, rec, offp, tab, deltas, C.c_uint(block_length), C.c_uint(57 - block_length), I(len(gps)), gpp, gip, grp, stats, output, U(262144), survivors, survivor_counts, C.c_uint(survivor_capacity), I(split_at), survivors2, survivor_counts2, I(split_second)]
        checked(gpu.cu.cuMemsetD8_v2(survivor_counts, C.c_ubyte(0), C.c_size_t(4 * len(ms))), 'zero compact counts')
        params = (P * len(argv))(*[C.cast(C.byref(v), P) for v in argv])
        begin = time.perf_counter()
        dargv = [U(start + done), C.c_uint(count), I(len(rad)), rp, op, cp, U(M), rootsbuf]
        dparams = (P * len(dargv))(*[C.cast(C.byref(v), P) for v in dargv])
        checked(gpu.cu.cuLaunchKernel(_cache['decoder'], (count + 63) // 64, 1, 1, 64, 1, 1, 0, None, dparams, None), 'decode roots')
        checked(gpu.cu.cuLaunchKernel(gpu.function, (count + 63) // 64, len(ms), 1, 64, 1, 1, 0, None, params, None), 'launch2D')
        checked(gpu.cu.cuCtxSynchronize(), 'stage1 sync')
        stage1_seconds += time.perf_counter() - begin
        td = time.perf_counter()
        sc = array.array('I')
        sc.frombytes(gpu.get(survivor_counts, 4 * len(ms)))
        compact_download_seconds += time.perf_counter() - td
        assert all((v <= count * max_words for v in sc))
        staged_words += sum(sc)
        nmax = max(sc)
        t2 = time.perf_counter()
        checked(gpu.cu.cuMemsetD8_v2(survivor_counts2, C.c_ubyte(0), C.c_size_t(4 * len(ms))), 'zero second compact counts')
        if nmax:
            checked(gpu.cu.cuLaunchKernel(_cache['middle'], (nmax + 63) // 64, len(ms), 1, 64, 1, 1, 0, None, params, None), 'middle compact words')
            checked(gpu.cu.cuCtxSynchronize(), 'middle sync')
        stage3_seconds += time.perf_counter() - t2
        td = time.perf_counter()
        sc2 = array.array('I')
        sc2.frombytes(gpu.get(survivor_counts2, 4 * len(ms)))
        compact_download_seconds += time.perf_counter() - td
        assert all((v <= sc[i] for i, v in enumerate(sc2)))
        second_staged_words += sum(sc2)
        nmax = max(sc2)
        t2 = time.perf_counter()
        if nmax:
            checked(gpu.cu.cuLaunchKernel(_cache['finisher'], (nmax + 63) // 64, len(ms), 1, 64, 1, 1, 0, None, params, None), 'finish compact words')
            checked(gpu.cu.cuCtxSynchronize(), 'stage2 sync')
        stage2_seconds += time.perf_counter() - t2
        dt = time.perf_counter() - begin
        launch_seconds += dt
        launches += 1
        maximum = max(maximum, dt)
        done += count
        tget = time.perf_counter()
        s = array.array('Q')
        s.frombytes(gpu.get(stats, 56))
        counter_seconds += time.perf_counter() - tget
        assert s[4] == 0 and s[3] < 262144 and (s[5] == done * len(ms)), s
        if time.perf_counter() - t >= cap or s[3] > 200000:
            break
        batch = max(256, min(root_capacity, int(count * min(4, max(0.25, 0.15 / max(dt, 1e-05))))))
    elapsed = time.perf_counter() - t
    rr = array.array('Q')
    rr.frombytes(gpu.get(output, 16 * s[3]))
    pairs = sorted(zip(rr[::2], rr[1::2]))
    assert len(pairs) == len(set(pairs))
    fields = dict(mode='universal-cached-roots', length=block_length, N=N, lower_end=lower, bound_kind='starting_value', base_step=g, K=K, first_mask=mask, first_root=start, completed_root=start + done - 1, root_limit=limit, timeout=int(start + done <= limit), seconds=elapsed, setup_seconds=setup, roots=s[5], root_batches=done, step_planes=len(ms), points=s[0], candidates=s[1], checks=s[2], passed=s[3], gap_checks=s[6], max_kernel_seconds=maximum, filter_limit=filter_limit, dense_limit=dense_limit, filter_rule=f'central_core_and_57_extension_no_inert_prime_le_{filter_limit}', multipliers=','.join(map(str, ms)))
    fields.update(diagnostic_check_counters='omitted', split_second=split_second, middle_stage_seconds=stage3_seconds, second_staged_words=second_staged_words, split_at=split_at, staged_words=staged_words, stage1_seconds=stage1_seconds, stage2_seconds=stage2_seconds, compact_download_seconds=compact_download_seconds, max_words_per_root=max_words, root_capacity=root_capacity, survivor_capacity=survivor_capacity, step_lower_bounds=','.join(map(str, los)), step_upper_bounds=','.join(map(str, his)), geometry_module=geometry_module, gap_floor=floor, cached_first_root=start + done - count, last_batch_count=count, maximum_batch_threads=maximum_threads, launches=launches, launch_sync_seconds=launch_seconds, counter_download_seconds=counter_seconds, other_host_seconds=elapsed - launch_seconds - counter_seconds)
    return (pairs, fields)
