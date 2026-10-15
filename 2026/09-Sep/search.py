import argparse
import hashlib
import json
import pathlib
import re
import time

from paths import ROOT

def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)

def certify(a, d, length, output):
    from certificate_math import factor, verify
    def good(n):
        return n >= 0 and (n == 0 or all(p % 3 != 2 or e % 2 == 0 for p, e in factor(n)))
    while good(a-d):
        a -= d
        length += 1
    while good(a+length*d):
        length += 1
    result = verify(a, d, length, output/'certificate.csv')
    result['neighbors'] = {str(n): factor(n) for n in (a-d, a+length*d) if n > 0}
    from verify import verify as check_identities
    check_identities(output/'certificate.csv', result)
    save(output/'solution.json', result)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--replay-hit', action='store_true')
    parser.add_argument('--budget', type=float, default=3600)
    parser.add_argument('--chunk', type=float, default=2)
    parser.add_argument('--output', type=pathlib.Path)
    args = parser.parse_args()
    if args.budget <= 0 or args.chunk <= 0:
        parser.error('Time limits must be positive.')
    mode = 'replay_hit' if args.replay_hit else 'search'
    output = (args.output or ROOT/'runs'/mode).resolve()
    output.mkdir(parents=True, exist_ok=True)
    plan_bytes = (ROOT/'plans.json').read_bytes()
    plans = json.loads(plan_bytes)[mode]
    fingerprint = hashlib.sha256(plan_bytes)
    for path in sorted(ROOT.iterdir()):
        if path.suffix in ('.py','.cpp','.h','.cu'):
            fingerprint.update(path.name.encode())
            fingerprint.update(path.read_bytes())
    identity = fingerprint.hexdigest()
    checkpoint = output/'checkpoint.json'
    if checkpoint.with_suffix('.json.tmp').exists():
        raise RuntimeError('Incomplete checkpoint write; inspect it before resuming.')
    if checkpoint.exists():
        state = json.loads(checkpoint.read_text())
        if state['fingerprint'] != identity or state['mode'] != mode:
            raise RuntimeError('Source or plan changed; use a different output directory.')
    else:
        state = dict(fingerprint=identity,mode=mode,region=0,next_root=plans[0]['start'],chunks=0,candidates=0,found=None)
        save(checkpoint,state)
    if state['found']:
        print(json.dumps(state['found']))
        return
    from gpu import GPU
    from native import check_pairs
    from sieve import gpu_chunk
    started = time.perf_counter()
    gpu = GPU(True, kernel_source='kernel.cu')
    try:
        while state['region'] < len(plans) and time.perf_counter()-started < args.budget:
            region = plans[state['region']]
            batch = output/f"chunk{state['chunks']:06}.json"
            if batch.exists():
                raise RuntimeError('Uncommitted batch exists; preserve and reconcile it before resuming.')
            pairs, metrics = gpu_chunk(gpu,region['N'],region['lower'],region['K'],region['mask'],state['next_root'],region['limit'],args.chunk,**region['options'])
            checked = check_pairs(pairs)
            save(batch,dict(region=region['id'],pairs=pairs,metrics=metrics,checked=checked))
            state['next_root'] = metrics['completed_root']+1
            state['chunks'] += 1
            state['candidates'] += len(pairs)
            for a,d,length,end in re.findall(r'VERIFIED a=(\d+) d=(\d+) length=(\d+) end=(\d+)',checked):
                if int(length)>=57:
                    state['found'] = certify(int(a),int(d),int(length),output)
                    save(checkpoint,state)
                    print(json.dumps(state['found']),flush=True)
                    return
            if state['next_root']>region['limit']:
                state['region']+=1
                if state['region']<len(plans):
                    state['next_root']=plans[state['region']]['start']
            save(checkpoint,state)
            print(json.dumps(dict(region=region['id'],chunks=state['chunks'],candidates=state['candidates'],elapsed_seconds=time.perf_counter()-started)),flush=True)
    finally:
        gpu.close()
    print(json.dumps(dict(status='bounded_stop',checkpoint=str(checkpoint),elapsed_seconds=time.perf_counter()-started)))

if __name__ == '__main__':
    main()
