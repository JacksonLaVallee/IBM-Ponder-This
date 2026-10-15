import os
import pathlib
import shutil
import subprocess
import sys

def main():
    root = pathlib.Path(__file__).resolve().parent
    output = root / '.build'
    output.mkdir(exist_ok=True)
    if sys.platform == 'win32':
        vcvars = os.environ.get('VCVARSALL')
        if not vcvars:
            installer = pathlib.Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Microsoft Visual Studio/Installer/vswhere.exe'
            if installer.exists():
                found = subprocess.check_output([str(installer), '-latest', '-products', '*', '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath'], text=True).strip()
                if found:
                    vcvars = str(pathlib.Path(found) / 'VC/Auxiliary/Build/vcvarsall.bat')
        if not shutil.which('cl') and not vcvars:
            raise SystemExit('Install Visual Studio C++ Build Tools, or run from an x64 Native Tools prompt.')
        for name in ('masks', 'inverse', 'checker'):
            command = f'cl /nologo /std:c++17 /O2 /EHsc /LD "{root / (name + ".cpp")}" /link /OUT:"{output / (name + ".dll")}"'
            if vcvars:
                command = f'call "{vcvars}" x64 >nul && {command}'
            subprocess.run(command, shell=True, cwd=output, check=True)
    else:
        compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
        if not compiler:
            raise SystemExit('A C++17 compiler is required.')
        for name in ('masks', 'inverse', 'checker'):
            subprocess.run([compiler, '-std=c++17', '-O3', '-shared', '-fPIC', str(root / (name + '.cpp')), '-o', str(output / (name + '.so'))], check=True)
    print('Native components built.')

if __name__ == '__main__':
    main()
