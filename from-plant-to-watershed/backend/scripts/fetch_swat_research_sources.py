#!/usr/bin/env python3
"""Fetch hash-pinned SWAT+ source/build packages into a local workspace cache.

This Linux x86_64 toolchain requires compatible Arch/CachyOS system libraries
and GCC support files. It does not install or update system packages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    scripts = Path(__file__).resolve().parent
    source = json.loads((scripts / "swat_research_source.lock.json").read_text())
    packages = json.loads((scripts / "swat_research_toolchain.lock.json").read_text())
    downloads = [{"filename": "source.tar.gz", "url": source["archive_url"], "sha256": source["archive_sha256"]}, *packages]
    for item in downloads:
        destination = args.cache / item["filename"]
        if not destination.exists():
            partial = destination.with_name(destination.name + ".partial")
            with urllib.request.urlopen(item["url"], timeout=60) as response, partial.open("wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            if hashlib.sha256(partial.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError(f"Downloaded archive differs from lock: {item['filename']}")
            partial.rename(destination)
        if hashlib.sha256(destination.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Existing archive differs from lock: {item['filename']}")
        print(f"Pinned archive: {destination}", flush=True)
    tools = args.cache / "toolchain"
    tools.mkdir(exist_ok=True)
    for item in packages:
        subprocess.run(["tar", "-xf", str(args.cache/item["filename"]), "-C", str(tools)], check=True)


if __name__ == "__main__":
    main()
