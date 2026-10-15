import array, ctypes as C, hashlib, pathlib, time
from paths import CACHE as W, ROOT
from runtime import load_runtime
U = C.c_uint64
I = C.c_int
P = C.c_void_p

def checked(code, where):
    if code:
        raise RuntimeError(f'{where}: error {code}')

class GPU:

    def __init__(self, wide_roots=False, kernel_source=None):
        self.wide_roots = wide_roots
        self.handle, self.nv, self.cu = load_runtime()
        self.allocations = []
        checked(self.cu.cuInit(0), 'cuInit')
        dev = I()
        checked(self.cu.cuDeviceGet(C.byref(dev), 0), 'device')
        self.ctx = P()
        checked(self.cu.cuDevicePrimaryCtxRetain(C.byref(self.ctx), dev), 'context')
        checked(self.cu.cuCtxSetCurrent(self.ctx), 'set context')
        src = (ROOT / (kernel_source or 'kernel.cu')).read_bytes()
        key = hashlib.sha256(src + b'compute89-fmadfalse').hexdigest()[:16]
        ptxfile = W / f'gpu48-{key}.ptx'
        if not ptxfile.exists():
            program = P()
            checked(self.nv.nvrtcCreateProgram(C.byref(program), src, b'gpu48.cu', 0, None, None), 'create program')
            opts = (C.c_char_p * 3)(b'--gpu-architecture=compute_89', b'--std=c++17', b'--fmad=false')
            status = self.nv.nvrtcCompileProgram(program, 3, opts)
            size = C.c_size_t()
            self.nv.nvrtcGetProgramLogSize(program, C.byref(size))
            log = C.create_string_buffer(size.value)
            self.nv.nvrtcGetProgramLog(program, log)
            (W / 'next48-gpu-compile.txt').write_bytes(log.value)
            checked(status, 'compile: ' + log.value.decode())
            checked(self.nv.nvrtcGetPTXSize(program, C.byref(size)), 'PTX size')
            ptx = C.create_string_buffer(size.value)
            checked(self.nv.nvrtcGetPTX(program, ptx), 'PTX')
            ptxfile.write_bytes(ptx.raw)
            self.nv.nvrtcDestroyProgram(C.byref(program))
        ptx = C.create_string_buffer(ptxfile.read_bytes())
        self.module = P()
        checked(self.cu.cuModuleLoadData(C.byref(self.module), ptx), 'load PTX')
        self.function = P()
        checked(self.cu.cuModuleGetFunction(C.byref(self.function), self.module, b'search'), 'kernel')

    def put(self, data):
        data = bytes(data)
        if not data:
            data = b'\x00'
        ptr = U()
        checked(self.cu.cuMemAlloc_v2(C.byref(ptr), C.c_size_t(len(data))), 'allocate')
        buf = C.create_string_buffer(data)
        checked(self.cu.cuMemcpyHtoD_v2(ptr, buf, C.c_size_t(len(data))), 'upload')
        self.allocations.append(ptr)
        return ptr

    def get(self, ptr, size):
        b = C.create_string_buffer(size)
        checked(self.cu.cuMemcpyDtoH_v2(b, ptr, C.c_size_t(size)), 'download')
        return b.raw

    def launch(self, args, count):
        params = (P * len(args))(*[C.cast(C.byref(v), P) for v in args])
        checked(self.cu.cuLaunchKernel(self.function, (count + 63) // 64, 1, 1, 64, 1, 1, 0, None, params, None), 'launch')
        checked(self.cu.cuCtxSynchronize(), 'sync')

    def close(self):
        for p in self.allocations:
            self.cu.cuMemFree_v2(p)
        self.allocations = []

def buf(code, values):
    return array.array(code, values).tobytes()
