import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = pathlib.Path(os.environ.get('LOESCH_CACHE', str(ROOT / '.cache')))
CACHE.mkdir(parents=True, exist_ok=True)

def library(name):
    suffix = '.dll' if sys.platform == 'win32' else '.so'
    path = ROOT / '.build' / (name + suffix)
    if not path.is_file():
        raise FileNotFoundError(f'{path.name} is missing; run python build.py')
    return path
