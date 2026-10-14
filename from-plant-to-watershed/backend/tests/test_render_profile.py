"""Regression checks for the small-instance deployment profile."""
from datetime import date
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import Settings, settings
from app.core.database import AsyncSessionLocal, Base, engine_options
from app.core.security import create_access_token
from app.main import app
from app.models.simulation import SimulationRun, PlaybackFrame
from app.models.user import User
from app.models.watershed import Watershed
from app.services.playback_database import PlaybackDatabaseStore
from app.services.playback_diagnostic import diagnose_simulation
from app.services.seed_service import bootstrap_system_reference_data, bootstrap_mvp_data
from app.schemas.playback import PlaybackPage
from scripts.generate_visual_fixtures import generate


def test_provider_urls_and_bounded_pool(monkeypatch):
    assert Settings(DATABASE_URL='postgres://user:password@host/db').DATABASE_URL.startswith('postgresql+asyncpg://')
    monkeypatch.setattr(settings, 'DB_POOL_SIZE', 2)
    monkeypatch.setattr(settings, 'DB_MAX_OVERFLOW', 0)
    url, options = engine_options('postgresql+asyncpg://user:password@host/db?sslmode=require')
    assert 'sslmode' not in url.query
    assert options['connect_args']['ssl'] == 'require'
    assert options['pool_size'] == 2 and options['max_overflow'] == 0
    assert 'pool_size' not in engine_options('sqlite+aiosqlite:///:memory:')[1]


@pytest.mark.asyncio
async def test_reference_bootstrap_has_no_accounts_or_runs(tmp_path):
    engine = create_async_engine(f'sqlite+aiosqlite:///{tmp_path}/reference.sqlite')
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as db:
            await bootstrap_system_reference_data(db)
            await bootstrap_mvp_data(db, create_demo_user=False)
            await bootstrap_mvp_data(db, create_demo_user=False)
            assert await db.scalar(select(func.count()).select_from(User)) == 0
            assert await db.scalar(select(func.count()).select_from(SimulationRun)) == 0
            assert await db.scalar(select(func.count()).select_from(Watershed)) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_streamed_availability_matches_full_diagnostic_and_rejects_late_corruption(monkeypatch):
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == 'admin@digitaltwin.org'))
        watershed = await db.scalar(select(Watershed))
        from app.models.simulation import ClimateScenario
        scenario = await db.scalar(select(ClimateScenario))
        identifier = str(uuid4())
        run = SimulationRun(id=identifier, user_id=user.id, watershed_id=watershed.id,
                            scenario_id=scenario.id, name='stream regression fixture', status='COMPLETED',
                            requested_config={'swat_plus': {'run_type': 'SWAT_MULTISCALE_COUPLED'}})
        db.add(run)
        await db.flush()
        records = [r.model_copy(update={'simulation_id': identifier}) for r in PlaybackPage.model_validate(generate()['pages']['coupled_daily']).records]
        manifest = await PlaybackDatabaseStore(db).write(identifier, records, provenance={'fixture': True})
        run.provenance = {'playback': manifest}
        await db.commit()
        expected = diagnose_simulation(run, on=date(2020, 5, 10), records_by_resolution={'DAILY': records})
        token = create_access_token(user.id)
    def forbidden(*args, **kwargs):
        pytest.fail('availability must not load the full year')
    monkeypatch.setattr(PlaybackDatabaseStore, 'records', forbidden)
    async with AsyncClient(transport=ASGITransport(app), base_url='http://test', headers={'Authorization': f'Bearer {token}'}) as client:
        response = await client.get(f'/api/v1/simulations/{identifier}/availability?date=2020-05-10')
        assert response.status_code == 200
        assert response.json() == expected.model_dump(mode='json')
        async with AsyncSessionLocal() as db:
            await db.execute(update(PlaybackFrame).where(PlaybackFrame.simulation_id == identifier,
                PlaybackFrame.date == records[-1].date).values(sha256='0' * 64))
            await db.commit()
        invalid = (await client.get(f'/api/v1/simulations/{identifier}/availability')).json()['resolutions'][0]
        assert invalid['artifact_status'] == 'INVALID'
        assert invalid['record_count'] == 0 and invalid['first_record'] is None


@pytest.mark.asyncio
async def test_single_simulation_slot_rejects_double_submit_and_releases(monkeypatch):
    from app.api.deps import single_simulation_slot
    monkeypatch.setattr(settings, 'SERIALIZE_SIMULATIONS', True)
    class Session:
        async def scalar(self, query):
            return None
    first = single_simulation_slot(Session(), SimpleNamespace())
    await anext(first)
    second = single_simulation_slot(Session(), SimpleNamespace())
    with pytest.raises(HTTPException) as error:
        await anext(second)
    assert error.value.status_code == 409
    await first.aclose()
    third = single_simulation_slot(Session(), SimpleNamespace())
    await anext(third)
    await third.aclose()


def test_swat_bundle_rejects_traversal_and_preserves_binary(tmp_path):
    import io
    import tarfile
    script = Path(__file__).resolve().parents[1] / 'deployment/swat_runtime.py'
    spec = importlib.util.spec_from_file_location('swat_runtime', script)
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'file.cio').write_text('fixture inputs')
    executable = tmp_path / 'fixture-engine'
    executable.write_bytes(b'fixture, not an executable SWAT model')
    archive = tmp_path / 'runtime.tar.gz'
    checksum = runtime.export_bundle(executable, project, archive)
    runtime.unpack(archive, tmp_path / 'unpacked')
    assert runtime.digest(tmp_path / 'unpacked/engine/swatplus') == runtime.digest(executable)
    assert len(checksum) == 64
    unsafe = tmp_path / 'unsafe.tar.gz'
    with tarfile.open(unsafe, 'w:gz') as tar:
        member = tarfile.TarInfo('../escape')
        member.size = 1
        tar.addfile(member, io.BytesIO(b'x'))
    with pytest.raises(ValueError, match='Unsafe'):
        runtime.unpack(unsafe, tmp_path / 'rejected')


def test_swat_output_tables_stream_without_whole_file_reads(tmp_path, monkeypatch):
    from app.services.swat_plus_parser import SwatOutputParser
    from app.services.swat_water_path import table, iter_table
    source = tmp_path / 'channel_day.txt'
    source.write_text('SWAT fixture\nyr mon day flo_out\nyyyy mm dd m3/s\n2020 1 1 4\n2020 1 2 5\n')
    def forbidden(*args, **kwargs):
        pytest.fail('output tables must stream instead of Path.read_text')
    monkeypatch.setattr(Path, 'read_text', forbidden)
    parser = SwatOutputParser()
    assert [row['streamflow_m3s'] for row in parser._read(source, {'streamflow_m3s'})] == [4, 5]
    assert [row['flo_out'] for row in iter_table(source)] == ['4', '5']
    repeatable = table(source)
    assert len(repeatable) == 2
    assert list(repeatable) == list(repeatable)


def test_bounded_weather_keeps_values_and_checks_duplicates_outside_period(tmp_path):
    from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader, SwatPlantMappingError
    source = tmp_path / 'weather.pcp'
    source.write_text('header\nstation\nunits\n2018 1 3\n2019 1 4\n2019 2 5\n')
    all_rows = SwatClimateForcingReader._numeric_rows(source, 3)
    bounded = SwatClimateForcingReader._numeric_rows(source, 3, start=date(2019, 1, 1), end=date(2019, 1, 2))
    assert bounded == {key: value for key, value in all_rows.items() if key[0] == 2019}
    source.write_text(source.read_text() + '2018 1 7\n')
    with pytest.raises(SwatPlantMappingError, match='Duplicate'):
        SwatClimateForcingReader._numeric_rows(source, 3, start=date(2019, 1, 1), end=date(2019, 1, 2))


def test_cloud_budget_rejects_large_run_without_changing_parameters(monkeypatch):
    from app.api.v1.simulations import _validate_runtime_budget
    monkeypatch.setattr(settings, 'SIMULATION_MAX_DAYS', 366)
    monkeypatch.setattr(settings, 'SIMULATION_MAX_PLANTS', 1000)
    request = SimpleNamespace(duration_days=365, plant_count=1000)
    _validate_runtime_budget(request)
    request.plant_count = 1001
    with pytest.raises(HTTPException) as error:
        _validate_runtime_budget(request)
    assert error.value.status_code == 422 and request.plant_count == 1001


def test_portable_runtime_command_preserves_elf_identity_and_rejects_changed_library(tmp_path):
    import hashlib
    import json
    from app.services.swat_research_engine import runtime_command
    engine = tmp_path / 'swatplus'
    engine.write_bytes(b'fixture executable identity')
    libraries = tmp_path / 'runtime'
    libraries.mkdir()
    loader = libraries / 'ld-linux.so'
    loader.write_bytes(b'fixture loader')
    marker = {'executable_sha256': hashlib.sha256(engine.read_bytes()).hexdigest(),
              'loader': loader.name, 'libraries': {loader.name: hashlib.sha256(loader.read_bytes()).hexdigest()}}
    (tmp_path / 'runtime-manifest.json').write_text(json.dumps(marker))
    command = runtime_command(engine)
    assert command[-1] == str(engine.resolve()) and command[0] == str(loader.resolve())
    loader.write_bytes(b'changed')
    with pytest.raises(ValueError, match='library checksum'):
        runtime_command(engine)
