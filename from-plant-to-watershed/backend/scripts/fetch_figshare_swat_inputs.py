#!/usr/bin/env python3
"""Fetch only reproducible SWAT+ *inputs* from a large public Figshare ZIP.

The TREC/Iowa State archive is 38+ GB because it intentionally includes GIS,
historical results and two study areas.  A SWAT+ run must never read those
historical results, so downloading the complete archive is both unnecessary and
unsafe on a workstation.  This small standard-library tool reads the ZIP64
central directory through HTTP ranges, retrieves only the requested TxtInOut
members, and emits a per-file checksum manifest.

It supports only stored and deflated ZIP members.  It does not synthesize any
input files and it rejects path traversal in archive member names.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


FIGSHARE_SWAT_ARCHIVE = "https://ndownloader.figshare.com/files/57107195"
BOONE_CDL_PREFIX = "SWAT+ Model Files/Boone Watershed/Boone_CDL_20250629/Scenarios/Default/TxtInOut/"
TAIL_BYTES = 4 * 1024 * 1024
EXCLUDED_SUFFIXES = ("_aa.txt", "_yr.txt", "_day.txt", "_mon.txt", ".out", ".exe", ".swf")
EXCLUDED_NAMES = {"fort.7777", "fort.7778"}
# The TREC package keeps a few historical diagnostics beside its inputs.  They
# are not named with the ordinary SWAT+ day/month/year suffixes, but are still
# generated result files and must never enter a reproducible source workspace.
EXCLUDED_HISTORICAL_OUTPUT_NAMES = {
    "__warnings.txt", "success.fin", "basin_carbon_all.txt", "basin_totc.txt",
    "erosion.txt", "lu_change_out.txt", "reservoir_sed.txt",
}
EXCLUDED_HISTORICAL_OUTPUT_SUFFIXES = (
    "_cbn_lyr.txt", "_cflux_stat.txt", "_orgc.txt", "_plc_stat.txt",
    "_resc_stat.txt", "_rsdc_stat.txt", "_soilc_stat.txt", "_totc.txt",
)


def _range_get(url: str, start: int, end: int) -> tuple[bytes, int]:
    request = Request(url, headers={"Range": f"bytes={start}-{end}", "User-Agent": "from-plant-to-watershed/phase-c"})
    with urlopen(request, timeout=120) as response:  # nosec B310 - explicit public Figshare URL
        payload = response.read()
        content_range = response.headers.get("Content-Range", "")
    try:
        total = int(content_range.rsplit("/", 1)[1])
    except (IndexError, ValueError) as exc:
        raise RuntimeError(f"server did not honor range request: {content_range!r}") from exc
    if len(payload) != end - start + 1:
        raise RuntimeError(f"range response length mismatch for bytes {start}-{end}")
    return payload, total


def _zip64_value(extra: bytes, *, compressed: int, uncompressed: int, offset: int) -> tuple[int, int, int]:
    cursor = 0
    while cursor + 4 <= len(extra):
        field_id, field_size = struct.unpack_from("<HH", extra, cursor)
        body = extra[cursor + 4:cursor + 4 + field_size]
        cursor += 4 + field_size
        if field_id != 0x0001:
            continue
        index = 0
        values = [uncompressed, compressed, offset]
        for position, value in enumerate(values):
            if value == 0xFFFFFFFF:
                if index + 8 > len(body):
                    raise RuntimeError("truncated ZIP64 extra field")
                values[position] = struct.unpack_from("<Q", body, index)[0]
                index += 8
        return values[1], values[0], values[2]
    if 0xFFFFFFFF in {compressed, uncompressed, offset}:
        raise RuntimeError("ZIP64 member is missing its ZIP64 extra field")
    return compressed, uncompressed, offset


def _central_directory(url: str) -> list[dict[str, int | str]]:
    # A one-byte probe gives the true archive size despite Figshare redirects.
    _, total = _range_get(url, 0, 0)
    start = max(0, total - TAIL_BYTES)
    tail, _ = _range_get(url, start, total - 1)
    eocd = tail.rfind(b"PK\x05\x06")
    if eocd < 0:
        raise RuntimeError("ZIP end-of-central-directory record was not found")
    normal_size, normal_offset = struct.unpack_from("<II", tail, eocd + 12)
    if normal_offset == 0xFFFFFFFF:
        locator = tail.rfind(b"PK\x06\x07", 0, eocd)
        if locator < 0:
            raise RuntimeError("ZIP64 locator was not found")
        zip64_offset = struct.unpack_from("<Q", tail, locator + 8)[0]
        local = zip64_offset - start
        if tail[local:local + 4] != b"PK\x06\x06":
            raise RuntimeError("ZIP64 end record is outside the requested archive tail")
        count = struct.unpack_from("<Q", tail, local + 32)[0]
        size = struct.unpack_from("<Q", tail, local + 40)[0]
        offset = struct.unpack_from("<Q", tail, local + 48)[0]
    else:
        count = struct.unpack_from("<H", tail, eocd + 10)[0]
        size, offset = normal_size, normal_offset
    location = offset - start
    if location < 0 or location + size > len(tail):
        raise RuntimeError("central directory does not fit in the requested archive tail")
    entries: list[dict[str, int | str]] = []
    for _ in range(count):
        if tail[location:location + 4] != b"PK\x01\x02":
            raise RuntimeError("invalid ZIP central-directory member")
        method = struct.unpack_from("<H", tail, location + 10)[0]
        compressed = struct.unpack_from("<I", tail, location + 20)[0]
        uncompressed = struct.unpack_from("<I", tail, location + 24)[0]
        name_length, extra_length, comment_length = struct.unpack_from("<HHH", tail, location + 28)
        relative_offset = struct.unpack_from("<I", tail, location + 42)[0]
        name_end = location + 46 + name_length
        name = tail[location + 46:name_end].decode("utf-8")
        extra = tail[name_end:name_end + extra_length]
        compressed, uncompressed, relative_offset = _zip64_value(
            extra, compressed=compressed, uncompressed=uncompressed, offset=relative_offset,
        )
        entries.append({"name": name, "method": method, "compressed": compressed,
                        "uncompressed": uncompressed, "offset": relative_offset})
        location = name_end + extra_length + comment_length
    return entries


def _is_input_member(name: str, prefix: str) -> bool:
    if not name.startswith(prefix) or name.endswith("/"):
        return False
    leaf = name.rsplit("/", 1)[-1]
    return (leaf not in EXCLUDED_NAMES and leaf not in EXCLUDED_HISTORICAL_OUTPUT_NAMES
            and not leaf.endswith(EXCLUDED_SUFFIXES)
            and not leaf.endswith(EXCLUDED_HISTORICAL_OUTPUT_SUFFIXES))


def _safe_relative(name: str, prefix: str) -> Path:
    relative = Path(name.removeprefix(prefix))
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"unsafe archive member {name!r}")
    return relative


def _extract_one(url: str, entry: dict[str, int | str], prefix: str, target: Path) -> dict[str, object]:
    name = str(entry["name"])
    offset, compressed_size = int(entry["offset"]), int(entry["compressed"])
    # Fetch local header plus payload.  Local headers can carry a different
    # extra-field length from their central-directory counterpart.
    header, _ = _range_get(url, offset, offset + 29)
    if header[:4] != b"PK\x03\x04":
        raise RuntimeError(f"invalid local ZIP member header for {name}")
    name_length, extra_length = struct.unpack_from("<HH", header, 26)
    first_data_byte = offset + 30 + name_length + extra_length
    payload, _ = _range_get(url, first_data_byte, first_data_byte + compressed_size - 1)
    method = int(entry["method"])
    if method == 0:
        data = payload
    elif method == 8:
        data = zlib.decompress(payload, -zlib.MAX_WBITS)
    else:
        raise RuntimeError(f"unsupported ZIP compression method {method} for {name}")
    if len(data) != int(entry["uncompressed"]):
        raise RuntimeError(f"uncompressed size mismatch for {name}")
    destination = target / _safe_relative(name, prefix)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_bytes(data)
    os.replace(temporary, destination)
    return {"member": name, "path": str(destination), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "compression_method": method}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=FIGSHARE_SWAT_ARCHIVE)
    parser.add_argument("--member-prefix", default=BOONE_CDL_PREFIX)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 16:
        raise SystemExit("--workers must be in 1..16")
    entries = [entry for entry in _central_directory(args.url) if _is_input_member(str(entry["name"]), args.member_prefix)]
    if not entries:
        raise SystemExit("no input members matched the requested prefix")
    args.destination.mkdir(parents=True, exist_ok=True)
    manifest_entries = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(_extract_one, args.url, entry, args.member_prefix, args.destination) for entry in entries]
        for future in as_completed(futures):
            manifest_entries.append(future.result())
    manifest = {
        "provider": "Iowa State University DataShare / Figshare",
        "dataset": "Tile Drainage and Rotation-Enhanced Cropland Data Layer",
        "doi": "10.25380/iastate.29869676.v1",
        "source_archive_url": args.url,
        "archive_file_id": 57107195,
        "archive_md5": "8dbd707aaaa8bdbad8b3aa2e039e723d",
        "member_prefix": args.member_prefix,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "processing_steps": ["ZIP64 central-directory range read", "retrieved TxtInOut inputs only", "excluded pre-existing SWAT+ output files and diagnostics"],
        "files": sorted(manifest_entries, key=lambda item: item["member"]),
    }
    (args.destination / "SOURCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(manifest_entries), "bytes": sum(int(item["bytes"]) for item in manifest_entries), "destination": str(args.destination)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
