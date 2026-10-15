import ctypes as C
import ctypes.util
import importlib.metadata
import os
import pathlib
import sys

def load_runtime():
    directories = []
    if os.environ.get('LOESCH_NVRTC_DIR'):
        directories.append(pathlib.Path(os.environ['LOESCH_NVRTC_DIR']))
    if os.environ.get('CUDA_PATH'):
        directories.append(pathlib.Path(os.environ['CUDA_PATH']) / 'bin')
    for package in ('nvidia-cuda-nvrtc-cu12', 'nvidia-cuda-nvrtc'):
        try:
            distribution = importlib.metadata.distribution(package)
            for file in distribution.files or []:
                if 'nvrtc' in file.name and ('.dll' in file.name or '.so' in file.name):
                    directories.append(pathlib.Path(distribution.locate_file(file)).parent)
        except importlib.metadata.PackageNotFoundError:
            pass
    directories = list(dict.fromkeys(directories))
    if sys.platform == 'win32':
        for directory in directories:
            choices = [p for p in directory.glob('nvrtc64_*.dll') if '.alt.' not in p.name]
            if choices:
                handle = os.add_dll_directory(str(directory))
                retained = [handle] + [C.WinDLL(str(p)) for p in directory.glob('nvrtc-builtins64_*.dll')]
                return retained, C.WinDLL(str(choices[0])), C.WinDLL('nvcuda.dll')
        raise RuntimeError('NVRTC missing; install requirements.txt or set LOESCH_NVRTC_DIR')
    for directory in directories:
        choices = sorted(directory.glob('libnvrtc.so*'))
        if choices:
            retained = [C.CDLL(str(p), mode=C.RTLD_GLOBAL) for p in directory.glob('libnvrtc-builtins.so*')]
            return retained, C.CDLL(str(choices[0])), C.CDLL('libcuda.so.1')
    name = ctypes.util.find_library('nvrtc')
    if name:
        return [], C.CDLL(name), C.CDLL('libcuda.so.1')
    raise RuntimeError('NVRTC missing; install requirements.txt')
