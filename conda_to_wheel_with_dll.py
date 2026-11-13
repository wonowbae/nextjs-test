#!/usr/bin/env python3
"""Offline Windows Conda -> wheel repackager with DLL bundling.

Run using the Python of the INSTALLED Anaconda environment.
Only stdlib is required. Windows CPython 3.8+ recommended.

Example:
    python conda_to_wheel_with_dll.py matplotlib -o C:\\wheelhouse
    python conda_to_wheel_with_dll.py matplotlib -o C:\\wheelhouse --extra-dll libexample.dll

This is an unofficial binary repackage, NOT equivalent to a correctly built
or audited upstream wheel. Only direct/transitive PE import DLLs found under
Conda Library/bin are copied. Runtime LoadLibrary() dependencies may be missed;
third-party Python dependencies are NOT bundled. No DLL name mangling is used.
"""

import argparse
import base64
import csv
import hashlib
import io
import json
import re
import struct
import sys
import sysconfig
import zipfile
from email.parser import Parser
from importlib import metadata
from pathlib import Path


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def list_files(record):
    """Conda 'files' and 'paths_data' are prefix-relative names with '/' separators."""
    p = record.get("paths_data", {}).get("paths", [])
    if p:
        return [entry["_path"] for entry in p if "_path" in entry]
    return record.get("files", [])


def sha256_digest(data):
    return 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode('ascii')


def pe_imports(path):
    """Read regular and delay-load DLL names from PE import tables.

    This deliberately uses only the Python standard library. It is not a full
    PE loader or dependency repairer, and does not detect LoadLibrary strings.
    """
    try:
        data = path.read_bytes()
    except OSError:
        return set(), 'read error'
    try:
        def u16(offset):
            return struct.unpack_from('<H', data, offset)[0]

        def u32(offset):
            return struct.unpack_from('<I', data, offset)[0]

        if data[:2] != b'MZ':
            return set(), 'not a PE file'
        pe = u32(0x3c)
        if data[pe:pe + 4] != b'PE\0\0':
            return set(), 'not a PE file'
        section_count = u16(pe + 6)
        optional_size = u16(pe + 20)
        opt = pe + 24
        magic = u16(opt)
        if magic == 0x20b:  # PE32+
            dir_start = opt + 112
            image_base = struct.unpack_from('<Q', data, opt + 24)[0]
        elif magic == 0x10b:  # PE32
            dir_start = opt + 96
            image_base = u32(opt + 28)
        else:
            return set(), 'unknown PE optional header'
        section_start = opt + optional_size
        sections = []
        for n in range(section_count):
            i = section_start + n * 40
            sections.append((u32(i + 12), max(u32(i + 8), u32(i + 16)), u32(i + 20)))

        def rva_offset(rva):
            for va, size, raw in sections:
                if va <= rva < va + size:
                    offset = raw + rva - va
                    return offset if 0 <= offset < len(data) else None
            # PE headers themselves can contain data.
            if 0 <= rva < section_start + section_count * 40:
                return rva
            return None

        def dll_at_rva(rva):
            offset = rva_offset(rva)
            if offset is None:
                return None
            end = data.find(b'\0', offset, min(len(data), offset + 260))
            if end < 0:
                return None
            name = data[offset:end].decode('ascii', errors='ignore').strip()
            return name if name.lower().endswith('.dll') else None

        found = set()
        # IMAGE_DIRECTORY_ENTRY_IMPORT = 1
        import_rva = u32(dir_start + 1 * 8)
        if import_rva:
            start = rva_offset(import_rva)
            if start is not None:
                for j in range(4096):
                    desc = start + j * 20
                    if desc + 20 > len(data):
                        break
                    descriptor = struct.unpack_from('<IIIII', data, desc)
                    if not any(descriptor):
                        break
                    name = dll_at_rva(descriptor[3])
                    if name:
                        found.add(name.lower())
        # IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT = 13
        delay_rva = u32(dir_start + 13 * 8)
        if delay_rva:
            start = rva_offset(delay_rva)
            if start is not None:
                for j in range(4096):
                    desc = start + j * 32
                    if desc + 32 > len(data):
                        break
                    words = struct.unpack_from('<IIIIIIII', data, desc)
                    if not any(words):
                        break
                    # Attributes bit 0: name field stores an RVA rather than VA
                    name_rva = words[1] if words[0] & 1 else words[1] - image_base
                    name = dll_at_rva(name_rva) if name_rva >= 0 else None
                    if name:
                        found.add(name.lower())
        return found, None
    except (IndexError, struct.error, ValueError, OverflowError):
        return set(), 'malformed PE file'


# System-provided DLLs and Python/runtime DLLs should not be copied out of
# an Anaconda prefix. All other missing names are printed for review.
SYSTEM_DLLS = {
    'kernel32.dll', 'kernelbase.dll', 'ntdll.dll', 'user32.dll', 'gdi32.dll',
    'gdi32full.dll', 'advapi32.dll', 'ole32.dll', 'oleaut32.dll', 'shell32.dll',
    'comdlg32.dll', 'comctl32.dll', 'rpcrt4.dll', 'secur32.dll', 'bcrypt.dll',
    'bcryptprimitives.dll', 'crypt32.dll', 'ws2_32.dll', 'winmm.dll',
    'version.dll', 'shlwapi.dll', 'shcore.dll', 'setupapi.dll', 'cfgmgr32.dll',
    'imm32.dll', 'psapi.dll', 'msvcrt.dll', 'ucrtbase.dll', 'normaliz.dll',
    'iphlpapi.dll', 'userenv.dll', 'dwmapi.dll', 'dbghelp.dll', 'opengl32.dll',
    'glu32.dll', 'd3d11.dll', 'dxgi.dll', 'winspool.drv', 'wldap32.dll',
    'netapi32.dll', 'dnsapi.dll', 'winhttp.dll', 'wininet.dll', 'hid.dll',
    'powrprof.dll', 'profapi.dll', 'combase.dll', 'sspicli.dll', 'cryptbase.dll',
}


def is_system_dll(name):
    name = name.lower()
    return (
        name in SYSTEM_DLLS or name.startswith(('api-ms-win-', 'ext-ms-win-'))
        or bool(re.fullmatch(r'python(?:3|\d{2,3}|\d{2,3}t)\.dll', name))
        or bool(re.fullmatch(r'vcruntime\d+(?:_\d+)?(?:_\d+)?\.dll', name))
        or name.startswith('msvcp140') or name.startswith('concrt140')
    )


def gather_dlls(binaries, lib_dir, extras):
    candidates = {p.name.lower(): p for p in lib_dir.glob('*.dll') if p.is_file()}
    bundled = {}  # lower name => Path
    unresolved = set()
    unparsed = []
    pending = list(binaries)
    seen = set()

    for extra in extras:
        name = Path(extra).name.lower()
        if name not in candidates:
            raise ValueError(f'--extra-dll {extra!r} not found in {lib_dir}')
        bundled[name] = candidates[name]
        pending.append(candidates[name])

    while pending:
        binary = pending.pop()
        identity = str(binary.resolve()).lower()
        if identity in seen:
            continue
        seen.add(identity)
        names, problem = pe_imports(binary)
        if problem:
            unparsed.append((binary.name, problem))
        for name in names:
            if is_system_dll(name):
                continue
            candidate = candidates.get(name)
            if candidate is None:
                unresolved.add(name)
                continue
            if name not in bundled:
                bundled[name] = candidate
                pending.append(candidate)
    return bundled, unresolved, unparsed


BOOTSTRAP_PY = '''"""Register DLL directory of an offline-repacked Matplotlib wheel."""
import os
from pathlib import Path

_DLL_DIRECTORY_HANDLES = []  # keep alive until interpreter exits
if os.name == "nt":
    _dll_dir = Path(__file__).resolve().parent / "matplotlib.libs"
    if _dll_dir.is_dir():
        if hasattr(os, "add_dll_directory"):
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(_dll_dir)))
        else:  # supported for older Python, although the wheel targets modern CPython
            os.environ["PATH"] = str(_dll_dir) + os.pathsep + os.environ.get("PATH", "")
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('name', help='PyPI distribution name, e.g. matplotlib')
    parser.add_argument('-o', '--output', default='wheelhouse', help='Target wheel directory')
    parser.add_argument('--extra-dll', action='append', default=[], metavar='NAME',
                        help='Also include this Library/bin DLL (for dynamic LoadLibrary calls); repeatable')
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Run this on Windows using the installed Anaconda Python.')
    if not hasattr(__import__('os'), 'add_dll_directory'):
        parser.error('Python 3.8 or newer required for reliable DLL loading.')

    name = normalize(args.name)
    prefix = Path(sys.prefix).resolve()
    site = Path(sysconfig.get_paths()['platlib']).resolve()
    meta_dir = prefix / 'conda-meta'
    lib_dir = prefix / 'Library' / 'bin'
    if not meta_dir.is_dir():
        parser.error(f'Not a Conda installation (missing {meta_dir})')
    if not lib_dir.is_dir():
        parser.error(f'No Conda Library/bin directory found: {lib_dir}')

    try:
        dist = metadata.distribution(name)
        version = dist.version
    except metadata.PackageNotFoundError:
        parser.error(f'{name} is not installed in {sys.executable}')

    distinfo = None
    for folder in site.glob('*.dist-info'):
        metapath = folder / 'METADATA'
        if not metapath.is_file():
            continue
        info = Parser().parsestr(metapath.read_text(encoding='utf-8', errors='replace'), headersonly=True)
        if normalize(info.get('Name', '')) == name and info.get('Version') == version:
            distinfo = folder
            break
    if distinfo is None:
        parser.error(f'Could not find .dist-info metadata for {name}=={version} in {site}')

    owners = []
    records = []
    for record_file in meta_dir.glob('*.json'):
        try:
            record = json.loads(record_file.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if normalize(record.get('name', '')) not in {name, name + '-base'}:
            continue
        owners.append(record['name'])
        records.append(list_files(record))
    if not records:
        parser.error(f'No installed Conda ownership record found for {name} or {name}-base')

    to_add = {}
    outside = set()
    for paths in records:
        for path in paths:
            src = prefix / Path(path.replace('/', '\\'))
            if not src.is_file():
                continue
            try:
                rel = src.resolve().relative_to(site).as_posix()
            except ValueError:
                outside.add(path)
                continue
            if '__pycache__' in rel.split('/') or src.suffix.lower() in ('.pyc', '.pyo'):
                continue
            if rel.startswith(distinfo.name + '/') and src.name in ('RECORD', 'WHEEL', 'INSTALLER', 'REQUESTED'):
                continue
            to_add[rel] = src

    for src in distinfo.rglob('*'):
        if src.is_file():
            rel = src.relative_to(site).as_posix()
            if src.name not in ('RECORD', 'WHEEL', 'INSTALLER', 'REQUESTED'):
                to_add[rel] = src

    # Some Conda versions have incomplete ownership records; gather Matplotlib's
    # own package files if the expected package is obviously incomplete.
    package_dir = site / name.replace('-', '_')
    if package_dir.is_dir() and not any(k.startswith(package_dir.name + '/') for k in to_add):
        for src in package_dir.rglob('*'):
            if src.is_file() and '__pycache__' not in src.parts and src.suffix.lower() not in ('.pyc', '.pyo'):
                to_add[src.relative_to(site).as_posix()] = src

    binaries = [p for p in to_add.values() if p.suffix.lower() in ('.pyd', '.dll')]
    if not binaries:
        print('WARNING: no native .pyd/.dll files were found in the package', file=sys.stderr)

    try:
        bundled, unresolved, unparsed = gather_dlls(binaries, lib_dir, args.extra_dll)
    except ValueError as e:
        parser.error(str(e))

    # Force a platform-specific wheel even when only data and pure Python were
    # found; the included DLLs are Windows-specific.
    if sys.implementation.name != 'cpython':
        parser.error('This script targets CPython')
    py = f'cp{sys.version_info.major}{sys.version_info.minor}'
    platform_tag = sysconfig.get_platform().replace('-', '_').replace('.', '_')
    tag = f'{py}-{py}-{platform_tag}'
    filename = f'{re.sub(r"[-_.]+", "_", name)}-{version.replace("-", "_")}-{tag}.whl'
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    wheel_path = output_dir / filename

    # .pth executes at startup, BEFORE a caller imports Matplotlib; without
    # this, Windows 3.8+ does not automatically search arbitrary package dirs.
    if bundled:
        bootstrap_name = '__offline_matplotlib_dll_bootstrap.py'
        pth_name = '__offline_matplotlib_dll_bootstrap.pth'
        if bootstrap_name in to_add or pth_name in to_add:
            parser.error('DLL bootstrap filename conflict in wheel contents')
        inline_files = {bootstrap_name: BOOTSTRAP_PY.encode('utf-8'),
                        pth_name: b'import __offline_matplotlib_dll_bootstrap\n'}
    else:
        inline_files = {}

    # Ensure pip considers the package installable as a wheel.
    wheel_info = ('Wheel-Version: 1.0\n'
                  'Generator: offline-conda-to-wheel-with-dll\n'
                  'Root-Is-Purelib: false\n'
                  f'Tag: {tag}\n').encode('utf-8')
    distinfo_rel = distinfo.name
    inline_files[f'{distinfo_rel}/WHEEL'] = wheel_info

    # DLL names are NOT mangled: if incompatible versions of the same named DLL
    # are already loaded elsewhere in the process, imports may still fail.
    for dll in bundled.values():
        rel = f'matplotlib.libs/{dll.name}'
        if rel in to_add or rel in inline_files:
            parser.error(f'archive path conflict: {rel}')
        to_add[rel] = dll

    rows = []
    with zipfile.ZipFile(wheel_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for rel, src in sorted(to_add.items()):
            content = src.read_bytes()
            archive.writestr(rel, content)
            rows.append((rel, sha256_digest(content), str(len(content))))
        for rel, content in sorted(inline_files.items()):
            archive.writestr(rel, content)
            rows.append((rel, sha256_digest(content), str(len(content))))
        rec_path = f'{distinfo_rel}/RECORD'
        rows.append((rec_path, '', ''))
        buf = io.StringIO(newline='')
        csv.writer(buf, lineterminator='\n').writerows(rows)
        archive.writestr(rec_path, buf.getvalue().encode('utf-8'))

    print(f'Created: {wheel_path}')
    print(f'Conda owners: {", ".join(owners)}')
    print(f'Package files: {len(to_add) - len(bundled)}')
    print(f'Included DLLs: {len(bundled)}')
    for dll in sorted(bundled.values(), key=lambda x: x.name.lower()):
        print(f'  + {dll.name}')
    if not bundled:
        print('WARNING: No DLLs from Conda Library/bin matched imported names.')
    if unresolved:
        print('REVIEW: DLL dependencies not found in Conda Library/bin:')
        for missing in sorted(unresolved):
            print('  ? ' + missing)
    if unparsed:
        print('REVIEW: binaries that were not parsed:')
        for binary, message in unparsed:
            print(f'  ? {binary}: {message}')
    if outside:
        print(f'NOTE: {len(outside)} Conda ownership files outside site-packages were not directly included.')
    print('NOTE: Python package dependencies (contourpy, Pillow, kiwisolver, etc.) are NOT bundled.')
    print('NOTE: No DLL renaming/conflict isolation or runtime LoadLibrary detection.')
    print('NOTE: Validate the wheel in a clean environment with the same Python ABI.')
    print('NOTE: Check redistribution licenses for any included DLLs.')


if __name__ == '__main__':
    main()
