"""Portable SWAT+ input/binary bundle; no generated simulation outputs or DB credentials."""
import argparse
import hashlib
import fnmatch
import sys
import subprocess
import re
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
from urllib.request import urlopen


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def unpack(archive, target):
    target = Path(target)
    with tarfile.open(archive, 'r:gz') as package:
        members = package.getmembers()
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                raise ValueError('Unsafe SWAT runtime archive member')
        if not {'engine/swatplus', 'project/file.cio'} <= {member.name for member in members}:
            raise ValueError('Archive requires engine/swatplus and project/file.cio')
        package.extractall(target, filter='data')
    (target / 'engine/swatplus').chmod(0o755)
    runtime = target / 'engine/runtime-manifest.json'
    if runtime.is_file():
        manifest = json.loads(runtime.read_text())
        (target / 'engine/runtime' / manifest['loader']).chmod(0o755)


def export_bundle(executable, project, output, bundle_system_runtime=False):
    executable, project, output = Path(executable), Path(project), Path(output)
    if not executable.is_file() or not (project / 'file.cio').is_file():
        raise ValueError('Supply the real SWAT executable and an input project with file.cio')
    if output.exists() or output.resolve().is_relative_to(project.resolve()):
        raise ValueError('Choose a new output outside the source project')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.services.swat_plus_adapter import _RECOGNIZED_OUTPUT_PATTERNS
    def inputs_only(member):
        if any(fnmatch.fnmatch(Path(member.name).name, pattern) for pattern in _RECOGNIZED_OUTPUT_PATTERNS):
            return None
        return member
    with tarfile.open(output, 'w:gz', dereference=True) as package:
        package.add(executable, arcname='engine/swatplus')
        engine_manifest = executable.parent / 'engine-manifest.json'
        if engine_manifest.is_file():
            package.add(engine_manifest, arcname='engine/engine-manifest.json')
        if bundle_system_runtime:
            linked = subprocess.check_output(['ldd', str(executable.resolve())], text=True)
            libraries = {Path(name) for name in re.findall(r'(/[^\s()]+)', linked)}
            if not libraries or any(not library.is_file() for library in libraries):
                raise ValueError('Cannot resolve the actual ELF runtime')
            loader = next(library for library in libraries if library.name.startswith('ld-linux'))
            manifest = {'executable_sha256': digest(executable), 'loader': loader.name,
                        'libraries': {library.name: digest(library) for library in sorted(libraries)}}
            for library in sorted(libraries):
                package.add(library, arcname='engine/runtime/' + library.name)
            import io
            data = json.dumps(manifest, sort_keys=True).encode()
            member = tarfile.TarInfo('engine/runtime-manifest.json')
            member.size = len(data)
            package.addfile(member, io.BytesIO(data))
        package.add(project, arcname='project', filter=inputs_only)
        # Adjacent calibration/input manifests remain part of scientific provenance.
        for name in ('manifest.json', 'frozen-plant-contract.json', 'parameter-manifest.json'):
            source = project.parent / name
            if source.is_file():
                package.add(source, arcname=name)
    return digest(output)


def install_bundle():
    url = os.environ.get('SWAT_RUNTIME_BUNDLE_URL', '')
    if not url:
        return  # Existing local installations continue to use their configured paths.
    checksum = os.environ.get('SWAT_RUNTIME_BUNDLE_SHA256', '')
    if not url.startswith('https://') or len(checksum) != 64 or any(c not in '0123456789abcdef' for c in checksum):
        raise ValueError('SWAT runtime requires HTTPS and its exact SHA256')
    target = Path(os.environ.get('SWAT_RUNTIME_DIR', 'data/swat-runtime'))
    marker = target / '.bundle-sha256'
    if marker.is_file() and marker.read_text().strip() == checksum:
        return
    if target.exists():
        raise ValueError('Runtime directory already exists with a different or incomplete bundle')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as scratch:
        archive = Path(scratch) / 'runtime.tar.gz'
        with urlopen(url, timeout=120) as response, archive.open('wb') as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        if digest(archive) != checksum:
            raise ValueError('SWAT runtime checksum mismatch')
        staging = Path(scratch) / 'unpacked'
        unpack(archive, staging)
        (staging / '.bundle-sha256').write_text(checksum + '\n')
        staging.rename(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('install')
    export = commands.add_parser('export')
    export.add_argument('--executable', required=True)
    export.add_argument('--project', required=True)
    export.add_argument('--output', required=True)
    export.add_argument('--bundle-system-runtime', action='store_true')
    args = parser.parse_args()
    if args.command == 'install':
        install_bundle()
    else:
        print(export_bundle(args.executable, args.project, args.output, args.bundle_system_runtime))
