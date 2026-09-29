"""Read-only owner-scoped inventory, including runs beyond the first 50.

Run from backend: venv/bin/python scripts/diagnose_simulations.py --user-id UUID
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.simulation import SimulationRun
from app.services.playback_diagnostic import diagnose_simulation


async def main(user_id: str | None):
    async with AsyncSessionLocal() as db:
        query = select(SimulationRun)
        if user_id is not None:
            query = query.where(SimulationRun.user_id == user_id)
        runs = list((await db.execute(query.order_by(SimulationRun.created_at.desc(), SimulationRun.id.desc()))).scalars())
        print(json.dumps({"count": len(runs), "runs": [
            {"owner_id": run.user_id, **diagnose_simulation(run).model_dump(mode="json", exclude={"simulation_name"})}
            for run in runs
        ]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--user-id")
    scope.add_argument("--all", action="store_true", help="Local administrative inventory of all owners")
    asyncio.run(main(parser.parse_args().user_id))
