import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings, settings
from app.core.migrations import SCHEMA_MIGRATIONS_DDL, apply_pending_migrations
from app.core.database import Base
from app.main import app
from app.models.simulation import ClimateScenario, SimulationRun
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
        assert versions == ["001_run_manifest_and_provenance.sql", "002_observational_registry.sql"]
        assert legacy_values[0] == "legacy-run"
        assert '"legacy":true' in legacy_values[1]
    finally:
        await engine.dispose()


def test_migration_sql_uses_portable_timestamp_types():
    migration_sql = (Path(__file__).parents[1] / "migrations" / "001_run_manifest_and_provenance.sql").read_text()
    assert "DATETIME" not in migration_sql.upper()
    assert "TIMESTAMP" in migration_sql
    assert "DATETIME" not in SCHEMA_MIGRATIONS_DDL.upper()
    assert "TIMESTAMP" in SCHEMA_MIGRATIONS_DDL


def test_websocket_rejects_anonymous_and_accepts_authenticated_playback():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as rejected:
            with client.websocket_connect("/api/v1/twin/ws/not-a-run"):
                pass
        assert rejected.value.code == 1008

        login = client.post("/api/v1/auth/login", json={
            "email": "investigador@digitaltwin.org", "password": "Investiga123!",
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        simulations = client.get("/api/v1/simulations", headers={"Authorization": f"Bearer {token}"})
        assert simulations.status_code == 200
        simulation_id = simulations.json()[0]["id"]
        with client.websocket_connect(f"/api/v1/twin/ws/{simulation_id}?token={token}") as websocket:
            tick = websocket.receive_json()
        assert tick["type"] == "SIMULATION_PLAYBACK_TICK"
        assert tick["evidence_type"] == "DEMO"
