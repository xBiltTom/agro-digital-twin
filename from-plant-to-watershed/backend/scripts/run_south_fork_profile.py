#!/usr/bin/env python3
"""Execute an owned research profile in the existing PostgreSQL database."""
import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
import app.models  # register all ORM tables
from app.models.simulation import SimulationRun
from app.services.south_fork_profile import create_profile, execute_profile, ProfileNotPending


async def main(args):
    url = make_url(settings.DATABASE_URL)
    if url.get_backend_name() != "postgresql" or url.database != "digitaltwin" or url.host not in {None,"localhost","127.0.0.1","::1"}:
        raise ValueError("Use existing pglocal digitaltwin")
    async with AsyncSessionLocal() as db:
        identifier = args.run_id
        if not identifier:
            if not args.owner:
                raise ValueError("Provide --run-id or --owner")
            sim = await create_profile(db,args.owner,args.year,args.arm,not args.no_ml)
            identifier = sim.id
            print(f"CREATED {identifier}",flush=True)
        try:
            sim = await execute_profile(db,identifier)
            print(f"COMPLETED {identifier}: {(sim.ml_result or {}).get('status')}",flush=True)
        except ProfileNotPending:
            raise
        except Exception as error:
            await db.rollback()
            sim = await db.get(SimulationRun,identifier)
            if sim is not None and sim.status in {"PENDING","RUNNING"}:
                sim.status = "FAILED"
                sim.error = {"message":str(error),"stage":"FROZEN_PROFILE_EXECUTION"}
                sim.finished_at = datetime.now(timezone.utc)
                await db.commit()
            raise
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    parser.add_argument("--owner")
    parser.add_argument("--year",type=int,choices=range(2021,2026),default=2025)
    parser.add_argument("--arm",choices=["A","B"],default="B")
    parser.add_argument("--no-ml",action="store_true")
    asyncio.run(main(parser.parse_args()))
