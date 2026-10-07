#!/usr/bin/env python3
"""Publish specified TEST B arms using the frozen runner, without reading observations.

Only schedule years the main runner has not reached. Distinct workspaces and
run IDs permit one additional worker on the local eight-core machine.
"""
import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import json

from run_south_fork_test import (
    AsyncSessionLocal, PROTOCOL, RUNTIME, engine, publish, sha256, verify_freeze, write_json,
)


async def main(years):
    protocol = json.loads(PROTOCOL.read_text())
    _, plants, _, frozen = verify_freeze(protocol)
    write_json(RUNTIME / "parallel-publication-receipt.json", {
        "scheduled_at_utc": datetime.now(timezone.utc).isoformat(), "years": years, "arm": "B",
        "wrapper_sha256": sha256(Path(__file__)), "frozen_runner_sha256": frozen["implementation_sha256"]["from-plant-to-watershed/backend/scripts/run_south_fork_test.py"],
        "scope": "Identical publish function, unique annual workspaces; no observations, fitting or evaluation"})
    try:
        for year in years:
            async with AsyncSessionLocal() as db:
                await publish(db, protocol, plants, year, "B")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("years", nargs="+", type=int, choices=range(2021, 2026))
    asyncio.run(main(parser.parse_args().years))
