import importlib
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings, settings
from app.core.migrations import SCHEMA_MIGRATIONS_DDL, apply_pending_migrations
from app.core.database import AsyncSessionLocal, Base
from app.main import app
from app.models.simulation import ClimateScenario, SimulationResult, SimulationRun
from app.models.user import Permission, Role, User
from app.models.watershed import PlantSpecies, Watershed
from app.services.seed_service import INITIAL_PERMISSIONS, INITIAL_ROLES


def test_runtime_security_rejects_placeholder_in_production():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings(APP_ENV="production", SECRET_KEY="CHANGE_ME").validate_runtime_security()
    with pytest.raises(RuntimeError, match="ENABLE_DEMO_SEED"):
        Settings(APP_ENV="production", SECRET_KEY="a-safe-production-secret-key", ENABLE_DEMO_SEED=True).validate_runtime_security()
    Settings(APP_ENV="development", SECRET_KEY="CHANGE_ME").validate_runtime_security()


@pytest.mark.asyncio
async def test_non_demo_bootstrap_creates_rbac_and_registers_default_role(tmp_path: Path, monkeypatch):
    """Exercise the actual registration endpoint against a clean, non-demo DB."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'non-demo.sqlite'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    main_module = importlib.import_module("app.main")
    database_module = importlib.import_module("app.core.database")
    monkeypatch.setattr(settings, "ENABLE_DEMO_SEED", False)
    monkeypatch.setattr(main_module, "engine", engine)
    monkeypatch.setattr(main_module, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(database_module, "engine", engine)
    monkeypatch.setattr(database_module, "AsyncSessionLocal", session_factory)

    try:
        with TestClient(main_module.app) as client:
            async with session_factory() as session:
                assert await session.scalar(select(func.count(Permission.id))) == len(INITIAL_PERMISSIONS)
                assert await session.scalar(select(func.count(Role.id))) == len(INITIAL_ROLES)
                assert await session.scalar(select(func.count(User.id))) == 0
                assert await session.scalar(select(func.count(PlantSpecies.id))) == 0
                assert await session.scalar(select(func.count(Watershed.id))) == 0
                assert await session.scalar(select(func.count(ClimateScenario.id))) == 0
                assert await session.scalar(select(func.count(SimulationRun.id))) == 0

            response = client.post("/api/v1/auth/register", json={
                "email": "new.operator@example.org",
                "password": "new-user-password",
                "full_name": "New Operator",
            })
            assert response.status_code == 201
            assert [role["name"] for role in response.json()["roles"]] == ["OPERADOR_AGROPECUARIO"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_admin_bootstraps_only_structural_data(tmp_path: Path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'admin.sqlite'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    cli_module = importlib.import_module("app.cli")
    monkeypatch.setattr(settings, "ENABLE_DEMO_SEED", False)
    monkeypatch.setattr(cli_module, "engine", engine)
    monkeypatch.setattr(cli_module, "AsyncSessionLocal", session_factory)

    try:
        await cli_module.create_admin("admin@example.org", "Initial Administrator", "test-only-admin-password")
        async with session_factory() as session:
            admin = await session.scalar(select(User).where(User.email == "admin@example.org"))
            assert admin is not None
            assert [role.name for role in admin.roles] == ["SUPERADMIN"]
            assert await session.scalar(select(func.count(ClimateScenario.id))) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_legacy_database_migration_is_idempotent(tmp_path: Path):
    database_path = tmp_path / "legacy.sqlite"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    try:
        async with engine.begin() as connection:
            await connection.exec_driver_sql("CREATE TABLE climate_scenarios (id VARCHAR PRIMARY KEY)")
            await connection.exec_driver_sql("CREATE TABLE simulation_runs (id VARCHAR PRIMARY KEY)")
            await connection.exec_driver_sql("CREATE TABLE simulation_results (id VARCHAR PRIMARY KEY)")
            await connection.exec_driver_sql("INSERT INTO simulation_runs (id) VALUES ('legacy-run')")

        await apply_pending_migrations(engine)
        await apply_pending_migrations(engine)

        async with engine.connect() as connection:
            columns = await connection.run_sync(
                lambda sync_connection: {
                    table: {column["name"] for column in inspect(sync_connection).get_columns(table)}
                    for table in ("climate_scenarios", "simulation_runs", "simulation_results")
                }
            )
            applied = await connection.exec_driver_sql("SELECT version FROM schema_migrations")
            versions = [row[0] for row in applied]
            legacy_row = await connection.exec_driver_sql("SELECT id, provenance FROM simulation_runs WHERE id = 'legacy-run'")
            legacy_values = legacy_row.one()
        assert {"source_type"} <= columns["climate_scenarios"]
        assert {"seed", "requested_config", "effective_config", "provenance", "error", "started_at", "finished_at"} <= columns["simulation_runs"]
        assert {"water_balance_residual_mm"} <= columns["simulation_results"]
        expected_versions = sorted(path.name for path in (Path(__file__).parents[1] / "migrations").glob("*.sql"))
        assert versions == expected_versions
        assert legacy_values[0] == "legacy-run"
        assert '"legacy":true' in legacy_values[1]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_unavailable_sap_flow_migration_preserves_legacy_rows_and_accepts_null(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'sap-flow.sqlite'}")
    try:
        async with engine.begin() as connection:
            await connection.exec_driver_sql("CREATE TABLE climate_scenarios (id VARCHAR PRIMARY KEY)")
            await connection.exec_driver_sql("CREATE TABLE simulation_runs (id VARCHAR PRIMARY KEY)")
            await connection.exec_driver_sql(
                "CREATE TABLE simulation_results (id VARCHAR PRIMARY KEY, sap_flow_velocity_cmh FLOAT NOT NULL)"
            )
            await connection.exec_driver_sql(
                "INSERT INTO simulation_results (id, sap_flow_velocity_cmh) VALUES ('legacy-result', 12.4)"
            )

        await apply_pending_migrations(engine)

        async with engine.begin() as connection:
            existing = await connection.exec_driver_sql(
                "SELECT sap_flow_velocity_cmh FROM simulation_results WHERE id='legacy-result'"
            )
            assert existing.scalar_one() == 12.4
            nullability = await connection.exec_driver_sql('PRAGMA table_info("simulation_results")')
            sap_column = next(row for row in nullability if row[1] == "sap_flow_velocity_cmh")
            assert sap_column[3] == 0
            await connection.exec_driver_sql(
                "INSERT INTO simulation_results (id, sap_flow_velocity_cmh) VALUES ('new-result', NULL)"
            )
            new_value = await connection.exec_driver_sql(
                "SELECT sap_flow_velocity_cmh FROM simulation_results WHERE id='new-result'"
            )
            assert new_value.scalar_one() is None
    finally:
        await engine.dispose()


def test_migration_sql_uses_portable_timestamp_types():
    migration_sql = (Path(__file__).parents[1] / "migrations" / "001_run_manifest_and_provenance.sql").read_text()
    assert "DATETIME" not in migration_sql.upper()
    assert "TIMESTAMP" in migration_sql
    assert "DATETIME" not in SCHEMA_MIGRATIONS_DDL.upper()
    assert "TIMESTAMP" in SCHEMA_MIGRATIONS_DDL


@pytest.mark.asyncio
async def test_websocket_rejects_anonymous_and_accepts_authenticated_playback():
    async with AsyncSessionLocal() as db:
        owner = await db.scalar(select(User).where(User.email == "admin@digitaltwin.org"))
        watershed = await db.scalar(select(Watershed).limit(1))
        scenario = await db.scalar(select(ClimateScenario).limit(1))
        run = SimulationRun(
            user_id=owner.id, watershed_id=watershed.id, scenario_id=scenario.id,
            name="WebSocket playback fixture", status="COMPLETED", duration_days=1,
            start_date=date(2020, 1, 1), end_date=date(2020, 1, 1), seed=9,
        )
        db.add(run)
        await db.flush()
        db.add(SimulationResult(
            simulation_run_id=run.id, day_index=1, date_str="2020-01-01",
            precip_mm=0.0, temp_c=18.0, solar_rad_mj=18.5,
            potential_et_mm=1.0, actual_et_mm=1.0, surface_runoff_mm=0.0,
            percolation_mm=0.0, streamflow_m3s=0.0, soil_moisture_vol=24.0,
            soil_water_depth_mm=180.0, plant_transpiration_mm=1.0,
            root_water_uptake_mm=1.0, cwsi_stress_index=0.0,
            sap_flow_velocity_cmh=None, water_balance_residual_mm=0.0,
        ))
        await db.commit()
        simulation_id = run.id

    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as rejected:
            with client.websocket_connect("/api/v1/twin/ws/not-a-run"):
                pass
        assert rejected.value.code == 1008

        # The legacy demo simulation belongs to the first seeded user
        # (SUPERADMIN); use its owner-scoped list for this websocket check.
        login = client.post("/api/v1/auth/login", json={
            "email": "admin@digitaltwin.org", "password": "Admin123!",
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        simulations = client.get("/api/v1/simulations", headers={"Authorization": f"Bearer {token}"})
        assert simulations.status_code == 200
        assert any(item["id"] == simulation_id for item in simulations.json())
        with client.websocket_connect(f"/api/v1/twin/ws/{simulation_id}?token={token}") as websocket:
            tick = websocket.receive_json()
        assert tick["type"] == "SIMULATION_PLAYBACK_TICK"
        assert tick["evidence_type"] == "DEMO"

    async with AsyncSessionLocal() as db:
        run = await db.scalar(select(SimulationRun).where(SimulationRun.id == simulation_id))
        await db.delete(run)
        await db.commit()


def test_final_scientific_report_requires_authentication_and_never_exposes_v1_as_current_v2():
    with TestClient(app) as client:
        assert client.get("/api/v1/reports/final-scientific").status_code == 401

        login = client.post("/api/v1/auth/login", json={
            "email": "investigador@digitaltwin.org", "password": "Investiga123!",
        })
        assert login.status_code == 200
        response = client.get(
            "/api/v1/reports/final-scientific",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )
        archive_response = client.get(
            "/api/v1/reports/final-scientific/archive-v1",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_contract"]["contract_version"] == "south-fork-final-v2"
    assert payload["current_contract"]["current_execution_status"] == "EXECUTED"
    assert payload["current_result"]["report_version"] == "south-fork-final-v2"
    assert payload["archived_result"]["report_version"] == "south-fork-final-v1"
    assert payload["archived_result"]["status"] == "ARCHIVED_HISTORICAL_RESULT"
    assert archive_response.status_code == 200
    assert archive_response.json()["not_current_contract_result"] is True
    assert "provenance" not in response.text
    assert "/home/" not in response.text
