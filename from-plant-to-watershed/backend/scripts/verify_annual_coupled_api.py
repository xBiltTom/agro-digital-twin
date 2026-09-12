"""Optional manual integration verification: API -> paired annual real SWAT+.

Environment supplies the executable, official Ames project, and an isolated SQLite
database. Heartbeats allow a terminal supervisor to keep this long real run alive.
"""
import asyncio
from datetime import date
import os
import threading
import time

from httpx import ASGITransport, AsyncClient

from app.core.database import Base, AsyncSessionLocal, engine
from app.core.security import create_access_token
from app.main import app
from app.models.simulation import ClimateScenario
from app.models.user import Role, User
from app.models.watershed import Watershed


async def initialize() -> str:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        role = Role(name="INVESTIGADOR_HIDROLOGO", description="real integration test")
        user = User(email="annual-api@test.local", hashed_password="not-used-by-token", full_name="Annual API test", is_active=True, is_verified=True, roles=[role])
        watershed = Watershed(code="AMES-API-TEST", name="Ames API integration", country="US", area_km2=1.0,
                              elevation_min_m=0.0, elevation_max_m=1.0, outlet_lat=42.04, outlet_lon=-93.89)
        scenario = ClimateScenario(code="AMES-API-CONTROL", name="Ames API control", pathway="CONTROL", description="API integration control", temp_anomaly_c=0.0, precip_factor=1.0, co2_ppm=400.0, source_type="SYNTHETIC")
        session.add_all([role, user, watershed, scenario])
        await session.commit()
        return user.id


async def exercise_api(user_id: str) -> dict:
    start, end = "1982-01-01", "1982-12-31"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {create_access_token(user_id)}"}
        watershed = (await client.get("/api/v1/simulations/watersheds/all", headers=headers)).json()[0]
        scenario = (await client.get("/api/v1/simulations/scenarios/all", headers=headers)).json()[0]
        request = {
            "name": "Annual Ames paired FSPM/SWAT+ verification", "watershed_id": watershed["id"], "scenario_id": scenario["id"],
            "duration_days": 365, "start_date": start, "end_date": end, "seed": 42, "plant_count": 1000,
            "mode": "SWAT_PLUS", "hydrology_backend": "SWAT_PLUS",
            "swat_plus": {"project_path": os.environ["SWAT_PLUS_COUPLED_PROJECT"], "executable_path": os.environ["SWAT_PLUS_EXECUTABLE"],
                          "working_directory": os.environ["SWAT_PLUS_COUPLED_WORKDIR"], "output_frequency": "DAILY", "timeout_seconds": 1200,
                          "run_type": "SWAT_MULTISCALE_COUPLED", "target_plant_name": "corn"},
        }
        response = await client.post("/api/v1/simulations", headers=headers, json=request)
        response.raise_for_status()
        coupled = response.json()
        outputs = await client.get(f"/api/v1/simulations/{coupled['id']}/swat-results", headers=headers)
        outputs.raise_for_status()
        return {"coupled": coupled, "swat_results": outputs.json()}


user_id = asyncio.run(initialize())
result: dict = {}
failure: list[BaseException] = []

def worker() -> None:
    try:
        result.update(asyncio.run(exercise_api(user_id)))
    except BaseException as exc:
        failure.append(exc)

thread = threading.Thread(target=worker, daemon=False)
thread.start()
while thread.is_alive():
    print("annual API/SWAT+ verification running", flush=True)
    time.sleep(5)
thread.join()
if failure:
    raise failure[0]
print({"coupled_id": result["coupled"]["id"], "provenance": result["coupled"]["provenance"], "summary": result["coupled"]["summary_metrics"], "record_count": len(result["swat_results"]["records"])}, flush=True)
