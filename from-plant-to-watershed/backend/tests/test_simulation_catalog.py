"""The catalogue must stay small even when scientific run results grow."""

import json
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select

from app.core.database import AsyncSessionLocal, engine
from app.core.security import create_access_token
from app.main import app
from app.models.simulation import ClimateScenario, SimulationRun
from app.models.user import User
from app.models.watershed import Watershed


@pytest.mark.asyncio
async def test_summary_catalog_projects_metadata_preserves_detail_and_owner_scope():
    async with AsyncSessionLocal() as db:
        owner = await db.scalar(select(User).where(User.email == "investigador@digitaltwin.org"))
        other = await db.scalar(select(User).where(User.email == "operador@digitaltwin.org"))
        watershed_id = await db.scalar(select(Watershed.id).limit(1))
        scenario_id = await db.scalar(select(ClimateScenario.id).limit(1))
        blob = "scientific-data-" * 10000
        run = SimulationRun(
            user_id=owner.id, watershed_id=watershed_id, scenario_id=scenario_id,
            name="Large catalogue regression", status="COMPLETED", duration_days=365,
            hydrology_backend="SWAT_PLUS", mode="SWAT_PLUS",
            provenance={"source_kind": "HISTORICAL_IMPORT", "evidence_type": "REAL_SWAT_PLUS_COUPLED",
                        "lineage": {"experiment_id": "historical-fixture"}, "process_logs": blob},
            requested_config={"swat_plus": {"run_type": "SWAT_MULTISCALE_COUPLED", "large_inputs": blob}},
            summary_metrics={"total_precip_mm": 12.5, "water_balance": {"large_output": blob}},
            hru_aggregates={"results": [blob]}, plant_sample=[{"large_sample": blob}],
            monthly_outputs=[{"large_output": blob}], validation={"large_validation": blob},
        )
        foreign_run = SimulationRun(
            user_id=other.id, watershed_id=watershed_id, scenario_id=scenario_id,
            name="Private foreign run", duration_days=1,
        )
        second_owned_run = SimulationRun(
            user_id=owner.id, watershed_id=watershed_id, scenario_id=scenario_id,
            name="Second visible run", duration_days=1,
        )
        db.add_all([run, foreign_run, second_owned_run])
        await db.commit()
        run_id, foreign_id = run.id, foreign_run.id
        token = create_access_token(owner.id)

    statements = []
    def capture(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           headers={"Authorization": f"Bearer {token}"}) as client:
        event.listen(engine.sync_engine, "before_cursor_execute", capture)
        try:
            response = await client.get("/api/v1/simulations?view=summary&limit=100")
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", capture)
        assert response.status_code == 200, response.text[:200]
        catalog = response.json()
        item = next(item for item in catalog if item["id"] == run_id)
        assert foreign_id not in {item["id"] for item in catalog}
        assert len(json.dumps(item)) < 4000
        assert item["scenario"]["id"] == scenario_id
        assert item["summary_metrics"] == {"total_precip_mm": 12.5}
        assert item["provenance"]["source_kind"] == "HISTORICAL_IMPORT"
        assert item["provenance"]["lineage"]["experiment_id"] == "historical-fixture"
        assert item["requested_config"]["swat_plus"]["run_type"] == "SWAT_MULTISCALE_COUPLED"
        assert not {"hru_aggregates", "monthly_outputs", "plant_sample", "validation"} & item.keys()
        # Inspect actual SQL so a response-only filter cannot reintroduce the cost.
        queries = [statement for statement in statements if "FROM simulation_runs" in statement]
        assert queries
        assert all("simulation_runs.hru_aggregates" not in query for query in queries)
        assert all("simulation_runs.monthly_outputs" not in query for query in queries)
        assert all("simulation_runs.plant_sample" not in query for query in queries)

        detail = await client.get(f"/api/v1/simulations/{run_id}")
        assert detail.status_code == 200
        assert detail.json()["provenance"]["process_logs"] == blob
        assert detail.json()["hru_aggregates"]["results"] == [blob]
        legacy = await client.get("/api/v1/simulations?limit=100")
        assert next(item for item in legacy.json() if item["id"] == run_id)["monthly_outputs"] == [{"large_output": blob}]
        assert (await client.get("/api/v1/simulations?view=unknown")).status_code == 422
        assert (await client.get("/api/v1/simulations?view=summary&limit=0")).status_code == 422
        first = (await client.get("/api/v1/simulations?view=summary&limit=1")).json()
        second = (await client.get("/api/v1/simulations?view=summary&limit=1&skip=1")).json()
        assert first and second and first[0]["id"] != second[0]["id"]
