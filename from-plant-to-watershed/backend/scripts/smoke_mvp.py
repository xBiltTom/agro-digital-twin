"""Run the authenticated end-to-end MVP request against the configured database."""

import asyncio
import json
from pathlib import Path
import sys
from time import perf_counter

from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app


async def main() -> None:
    started = perf_counter()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://mvp.local") as client:
        login = await client.post("/api/v1/auth/login", json={
            "email": "investigador@digitaltwin.org", "password": "Investiga123!",
        })
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        watersheds = (await client.get("/api/v1/simulations/watersheds/all", headers=headers)).json()
        scenarios = (await client.get("/api/v1/simulations/scenarios/all", headers=headers)).json()
        models = (await client.get("/api/v1/models", headers=headers)).json()
        watershed = next(item for item in watersheds if item["code"] == "USGS-05451210-PARTIAL")
        scenario = next(item for item in scenarios if item["code"] == "MVP_CONTROL")
        response = await client.post("/api/v1/simulations", headers=headers, json={
            "name": "POSTGRESQL SMOKE — 1000 plantas / USGS 05451210",
            "watershed_id": watershed["id"], "scenario_id": scenario["id"],
            "duration_days": 90, "seed": 20260907, "plant_count": 1000,
            "mode": "ML_ASSISTED" if models else "REAL_OBSERVATION",
            "external_model_id": models[0]["id"] if models else None,
            "hydrology_backend": "SIMPLIFIED", "start_date": "2020-01-01", "parameters": {},
        })
        response.raise_for_status()
        run = response.json()
    report = {
        "run_id": run["id"], "status": run["status"], "database": "PostgreSQL (configured runtime)",
        "plant_count": run["plant_count"], "field": run["field_aggregates"],
        "hru_count": run["hru_aggregates"]["count"], "hydrology_backend": run["hydrology_backend"],
        "external_model": run["ml_result"], "validation": run["validation"],
        "duration_seconds": round(perf_counter() - started, 3),
    }
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
