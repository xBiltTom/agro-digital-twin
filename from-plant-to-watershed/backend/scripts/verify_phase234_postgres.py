"""Read-only FastAPI verification of the corrected South Fork PostgreSQL playback."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.main import app
from app.models.simulation import SimulationRun
from app.services.playback_artifact import PlaybackArtifactStore

RUN_ID = "phase234-sf-2019-v2"
EXAMPLE = BACKEND / "data/phase1-south-fork-2019/results" / RUN_ID / "playback_api_example_2019-07-15.json"


async def verify_once(*, save_example: bool) -> dict:
    async with AsyncSessionLocal() as db:
        run = await db.get(SimulationRun, RUN_ID)
        if run is None or run.status != "COMPLETED":
            raise AssertionError("Corrected South Fork run is absent or incomplete")
        token = create_access_token(run.user_id)
    headers = {"Authorization": f"Bearer {token}"}
    root = f"/api/v1/simulations/{RUN_ID}"
    summary = {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://local", headers=headers) as client:
        for day in ("2019-01-15", "2019-05-15", "2019-07-15", "2019-08-30", "2019-09-15", "2019-12-15"):
            response = await client.get(root + "/playback", params={"date": day, "resolution": "DAILY"})
            assert response.status_code == 200, (day, response.status_code, response.text[:200])
            page = response.json()
            assert page["artifact_status"] == "AVAILABLE" and page["total"] == 1
            assert page["resolution"] == "DAILY" and page["available_resolutions"] == ["DAILY"]
            frame = page["records"][0]
            assert frame["date"] == day and len(frame["hru_results"]) == 36
            assert len(frame["channel_results"]) == 37
            assert frame["hydrology"]["streamflow_m3s"]["unit"] == "m3/s"
            assert frame["hru_results"][0]["hru_id"]
            assert frame["channel_results"][0]["channel_id"]
            active = frame["crop"]["active"]
            samples = len(frame["plant_samples"])
            if day in {"2019-01-15", "2019-09-15", "2019-12-15"}:
                assert not active and samples == 0
            if day == "2019-07-15":
                assert active and samples > 0
                water = frame["field"]["soil_moisture_vol_percent"]
                assert water["availability"] == "AVAILABLE" and water["evidence"] == "DERIVED"
                assert water["unit"] == "volumetric percent"
                assert frame["field"]["water_stress"]["availability"] == "AVAILABLE"
                assert frame["plant_samples"][0]["hru_ids"]
                if save_example:
                    EXAMPLE.write_text(json.dumps(page, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            summary[day] = {"crop_active": active, "plant_samples": samples,
                            "hru_count": len(frame["hru_results"]),
                            "channel_count": len(frame["channel_results"])}
        availability = await client.get(root + "/availability", params={"date": "2019-07-15"})
        assert availability.status_code == 200, availability.text[:200]
        assert availability.json()["resolutions"][0]["record_count"] == 365
        assert availability.json()["resolutions"][0]["selected_date"]["date"] == "2019-07-15"
        page = await client.get(root + "/playback", params={"start": "2019-07-01", "end": "2019-07-31", "offset": 10, "limit": 2})
        assert page.status_code == 200 and page.json()["total"] == 31
        assert [item["date"] for item in page.json()["records"]] == ["2019-07-11", "2019-07-12"]
    return summary


async def main() -> None:
    url = make_url(settings.DATABASE_URL)
    if url.get_backend_name() != "postgresql" or url.database != "digitaltwin":
        raise RuntimeError("Verification requires the existing local digitaltwin PostgreSQL database")
    # Any attempted legacy sidecar read fails immediately during verification.
    def no_sqlite(*_args, **_kwargs):
        raise AssertionError("FastAPI attempted to query a SQLite playback sidecar")
    PlaybackArtifactStore.page = no_sqlite
    PlaybackArtifactStore.iter_records = no_sqlite
    async with app.router.lifespan_context(app):
        first = await verify_once(save_example=True)
    async with app.router.lifespan_context(app):
        second = await verify_once(save_example=False)
    assert first == second
    print(json.dumps({"database": "digitaltwin/PostgreSQL", "restart_verified": True,
                      "sqlite_sidecar_reads": 0, "dates": second,
                      "example": str(EXAMPLE.relative_to(BACKEND.parent))}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
