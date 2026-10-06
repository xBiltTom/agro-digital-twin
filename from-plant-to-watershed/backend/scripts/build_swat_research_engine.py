#!/usr/bin/env python3
"""Build the pinned SWAT+ source with an explicit numerical/output policy.

Downloads are a separate step: supply the archived source and compiler/build
tools. No model equations are changed. Existing destinations are rejected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

COMMIT = "77b722bac716c32f2fba6b4e3f9dd6ea4b008e3d"
TAG = "61.0.2.61"
STORAGE_FILE = "channel_storage_day.txt"
STORAGE_MARKER = "channel-storage/v1"

DECLARATION = '''      integer, save :: storage_unit = 0
'''
OUTPUT = '''          ! Research diagnostic: read existing states/fluxes without changing them.
          if (storage_unit == 0) then
            open (newunit=storage_unit, file="channel_storage_day.txt", status="replace", action="write")
            write (storage_unit,'(a)') "SWAT+ Rev 2026.61.0.2.61 channel-storage/v1"
            write (storage_unit,'(a)') "jday mon day yr unit gis_id name ch_stor fp_stor tot_stor wet_stor inflow outflow precip evap seep ch_initial_routing fp_initial_routing"
            write (storage_unit,'(a)') "- - - - - - - m3 m3 m3 m3 m3 m3 m3 m3 m3 m3 m3"
          end if
          write (storage_unit,'(6(i0,1x),a,11(1x,es25.16e3))') &
            time%day, time%mo, time%day_mo, time%yrc, ichan, ob(iob)%gis_id, trim(ob(iob)%name), &
            real(ch_stor(ichan)%flo,8), real(fp_stor(ichan)%flo,8), real(tot_stor(ichan)%flo,8), &
            real(wet_stor(ichan)%flo,8), real(ob(iob)%hin%flo,8), real(ob(iob)%hd(1)%flo,8), &
            real(ch_wat_d(ichan)%precip,8), real(ch_wat_d(ichan)%evap,8), real(ch_wat_d(ichan)%seep,8), &
            real(ch_fp_wb(ichan)%ch_stor_init,8), real(ch_fp_wb(ichan)%fp_stor_init,8)
'''

# GNU Fortran's runtime bounds-check strings retain absolute input filenames
# even with -ffile-prefix-map. Pass stable relative filenames to the compiler.
LAUNCHER = '''import os
from pathlib import Path
import sys
command = sys.argv[1:]
for index, argument in enumerate(command[1:], 1):
    if argument.endswith(".f90") and Path(argument).is_absolute():
        command[index] = os.path.relpath(argument)
os.execv(command[0], command)
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text()
    if content.count(old) != 1:
        raise ValueError(f"Pinned source patch context changed: {path.name}")
    path.write_text(content.replace(old, new))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--cmake", type=Path, required=True)
    parser.add_argument("--toolchain-lock", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text())
    toolchain_lock = json.loads(args.toolchain_lock.read_text())
    for item in toolchain_lock:
        package = args.archive.resolve().parent / item["filename"]
        if sha(package) != item["sha256"]:
            raise ValueError(f"Compiler/build package differs from lock: {package.name}")
    if lock["commit"] != COMMIT or lock["tag"] != TAG or sha(args.archive) != lock["archive_sha256"]:
        raise ValueError("Source archive does not match the committed lock")
    if args.output.exists():
        raise ValueError("Preserve previous builds; choose a new output directory")
    root = args.output.resolve()
    root.mkdir(parents=True)
    with tarfile.open(args.archive) as archive:
        members = [member for member in archive.getmembers()
                   if member.name.startswith(f"swatplus-{COMMIT}/src/") or
                   member.name == f"swatplus-{COMMIT}/CMakeLists.txt"]
        archive.extractall(root, members=members, filter="data")
    source = root / f"swatplus-{COMMIT}"
    originals = {name: sha(source / name) for name in ("CMakeLists.txt", "src/sd_channel_output.f90")}
    cmake = source / "CMakeLists.txt"
    content = cmake.read_text()
    traps = "-ffpe-trap=invalid,zero,overflow,underflow"
    if content.count(traps) != 2:
        raise ValueError("Unexpected official numerical policy")
    cmake.write_text(content.replace(traps, "-ffpe-trap=invalid,zero,overflow"))
    output = source / "src/sd_channel_output.f90"
    replace_once(output, "      iob = sp_ob1%chandeg + ichan - 1", DECLARATION + "\n      iob = sp_ob1%chandeg + ichan - 1")
    replace_once(output, '        if (pco%sd_chan%d == "y") then', '        if (pco%sd_chan%d == "y") then\n' + OUTPUT)
    env = dict(os.environ, SOURCE_DATE_EPOCH="1768521600", TZ="UTC", LC_ALL="C")
    tool_lib = args.cmake.resolve().parent.parent / "lib"
    env["LD_LIBRARY_PATH"] = str(tool_lib)
    support = Path(subprocess.check_output(["gcc", "-print-libgcc-file-name"], text=True).strip()).parent
    frontend = Path(subprocess.check_output([str(args.compiler.resolve()), "-print-prog-name=f951"], text=True, env=env).strip())
    build = root / "build"
    launcher = root / "relative_compiler.py"
    launcher.write_text(LAUNCHER)
    commands = [[str(args.cmake.resolve()), "-S", str(source), "-B", str(build),
                 "-DCMAKE_BUILD_TYPE=Release", f"-DTAG={TAG}", "-DBUILD_TESTING=OFF",
                 f"-DCMAKE_Fortran_COMPILER={args.compiler.resolve()}",
                 f"-DCMAKE_Fortran_COMPILER_LAUNCHER={sys.executable};{launcher}",
                 f"-DCMAKE_Fortran_FLAGS=-B{support}/ -ffile-prefix-map={root}=swat-research"],
                [str(args.cmake.resolve()), "--build", str(build), "--parallel", str(args.jobs)]]
    with (root / "build.log").open("w") as log:
        for command in commands:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    binary = build / f"swatplus-{TAG}-gnu-lin_x86_64-Rel"
    destination = root / "swatplus-research"
    shutil.copy2(binary, destination)
    dependencies = subprocess.check_output(["ldd", str(destination)], text=True)
    dependency_hashes = {}
    for line in dependencies.splitlines():
        for token in line.split():
            if token.startswith("/") and Path(token).is_file():
                dependency_hashes[token] = sha(Path(token))
    manifest = {"schema_version": "swat-research-build/v1", "official_release": False,
        "source": {**lock, "archive": str(args.archive.resolve())},
        "executable": str(destination), "executable_sha256": sha(destination),
        "builder_sha256": sha(Path(__file__)), "source_date_epoch": env["SOURCE_DATE_EPOCH"],
        "compiler_launcher_sha256": sha(launcher),
        "compiler": subprocess.check_output([str(args.compiler.resolve()), "--version"], text=True, env=env).splitlines()[0],
        "compiler_sha256": sha(args.compiler.resolve()),
        "compiler_frontend_sha256": sha(frontend),
        "gcc_support": {str(path): sha(path) for name in ("libgcc.a", "libgcc_s.so", "liblto_plugin.so", "crtbeginS.o", "crtendS.o")
            if (path := support / name).is_file()},
        "cmake": subprocess.check_output([str(args.cmake.resolve()), "--version"], text=True, env=env).splitlines()[0],
        "cmake_sha256": sha(args.cmake.resolve()), "toolchain_packages": toolchain_lock,
        "effective_flags": (build / f"CMakeFiles/swatplus-{TAG}-gnu-lin_x86_64-Rel.dir/flags.make").read_text(),
        "commands": commands, "numerical_policy": {"trap": ["invalid", "zero", "overflow"], "allow": ["underflow"]},
        "patches": {name: {"before_sha256": checksum, "after_sha256": sha(source/name)}
                    for name, checksum in originals.items()},
        "storage_output": {"filename": STORAGE_FILE, "marker": STORAGE_MARKER,
            "precision": "Existing single precision states promoted to real(8) for round-trip decimal output; no extra model precision.",
            "timing": "sd_channel_output daily end-of-day; same sd_chan/day_print/interval conditions as channel_sd_day."},
        "dynamic_libraries_sha256": dependency_hashes, "build_log_sha256": sha(root/"build.log"),
        "limitations": ["Research build with output instrumentation; not an official SWAT+ release.",
            "A fixed recipe is reproducible with the recorded compiler and runtime libraries; compiler changes can alter results."]}
    (root / "engine-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"executable": str(destination), "sha256": manifest["executable_sha256"]}), flush=True)


if __name__ == "__main__":
    main()
