import csv
import json
import pathlib
import time

def verify(certificate=None, solution=None):
    root = pathlib.Path(__file__).resolve().parent
    certificate = pathlib.Path(certificate) if certificate else root / 'certificate.csv'
    solution = solution or json.loads((root / 'solution.json').read_text())
    started = time.perf_counter()
    with certificate.open(newline='') as file:
        rows = list(csv.DictReader(file))
    if len(rows) != solution['length'] or solution['d'] <= 0:
        raise ValueError('Invalid certificate length or step')
    for k, row in enumerate(rows):
        n, x, y = (int(row[t]) for t in ('n', 'x', 'y'))
        if int(row['index']) != k or n != solution['a'] + k * solution['d'] or n != x*x + x*y + y*y:
            raise ValueError(f'Invalid term {k}')
    if solution['end'] != solution['a'] + (len(rows)-1)*solution['d']:
        raise ValueError('Invalid endpoint')
    return dict(verified=True, length=len(rows), seconds=time.perf_counter()-started)

if __name__ == '__main__':
    print(json.dumps(verify()))
