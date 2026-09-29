"""Exercise the JSONB migration and frame store in an isolated PostgreSQL database."""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
import sys
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.core.database import Base
from app.core.migrations import apply_pending_migrations
from app.models.simulation import ClimateScenario, SimulationRun
from app.models.user import User
from app.models.watershed import Watershed
from app.schemas.playback import PlaybackRecord
from app.services.playback_database import PlaybackDatabaseStore


async def main() -> None:
    configured = make_url(settings.DATABASE_URL)
    if configured.get_backend_name() != "postgresql" or configured.database != "digitaltwin":
        raise RuntimeError("The local application must target digitaltwin/PostgreSQL")
    isolated = configured.set(database="digitaltwin_test_playback")
    engine = create_async_engine(isolated)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await apply_pending_migrations(engine)
        async with engine.connect() as connection:
            column_type = await connection.scalar(text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='playback_frames' AND column_name='payload'"
            ))
            assert column_type == "jsonb", column_type
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        run_id = str(uuid4())
        async with session_factory() as db:
            owner = User(email=f"playback-{run_id}@test.invalid", full_name="Isolated test", hashed_password="unused")
            watershed = Watershed(code=f"TEST-{run_id}", name="Isolated test", area_km2=1, outlet_lat=0, outlet_lon=0)
            scenario = ClimateScenario(code=f"TEST-{run_id}", name="Isolated test", pathway="test", description="test")
            db.add_all([owner, watershed, scenario])
            await db.flush()
            db.add(SimulationRun(id=run_id, user_id=owner.id, watershed_id=watershed.id,
                                 scenario_id=scenario.id, name="Isolated playback test", status="COMPLETED"))
            await db.flush()
            frames = [PlaybackRecord(simulation_id=run_id, date=day, resolution="DAILY",
                                     run_type="SWAT_STANDARD_BASELINE", watershed_id=watershed.id,
                                     spatial_support="TEST") for day in (date(2019, 1, 1), date(2019, 1, 2))]
            store = PlaybackDatabaseStore(db)
            manifest = await store.write(run_id, frames, provenance={"test": True})
            assert manifest["storage"] == "POSTGRESQL_JSONB" and manifest["record_count"] == 2
            repeated = await store.write(run_id, frames, provenance={"test": True}, idempotent=True)
            assert repeated["record_count"] == 2
            await db.commit()
        await engine.dispose()
        engine = create_async_engine(isolated)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            store = PlaybackDatabaseStore(db)
            total, page = await store.page(run_id, "DAILY", start=date(2019, 1, 1),
                                           end=date(2019, 1, 2), offset=1, limit=1)
            assert total == 2 and [row.date for row in page] == [date(2019, 1, 2)]
            conflict = frames[0].model_copy(update={"run_type": "SWAT_MULTISCALE_COUPLED"})
            try:
                await store.write(run_id, [conflict, frames[1]], provenance={}, idempotent=True)
            except ValueError as exc:
                assert "differs" in str(exc)
            else:
                raise AssertionError("Conflicting idempotent import was accepted")
        print("isolated PostgreSQL JSONB migration, idempotent import, pagination and reconnect: PASS")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
