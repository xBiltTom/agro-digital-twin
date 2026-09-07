import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.security import hash_password
from app.core.config import settings
from app.models.user import User, Role, Permission, UserProfile
from app.models.watershed import Watershed, Subbasin, HRU, PlantSpecies
from app.models.simulation import ClimateScenario, SimulationRun
from app.services.twin_coupling_engine import TwinCouplingEngine

logger = logging.getLogger(__name__)

INITIAL_PERMISSIONS = [
    {"name": "users:read", "description": "Consultar lista y detalle de usuarios"},
    {"name": "users:write", "description": "Crear y actualizar usuarios"},
    {"name": "users:delete", "description": "Desactivar usuarios del sistema"},
    {"name": "roles:read", "description": "Consultar roles y permisos"},
    {"name": "simulations:create", "description": "Crear experimentos con los modelos simplificados"},
    {"name": "simulations:read", "description": "Consultar simulaciones y resultados"},
    {"name": "simulations:execute", "description": "Ejecutar acoplamiento de gemelo digital"},
    {"name": "digital_twin:view_3d", "description": "Acceso al visor 3D multiescala"},
    {"name": "digital_twin:control", "description": "Control de parámetros y forzamiento ambiental"},
    {"name": "reports:generate", "description": "Generar reportes PDF, Word y Excel"},
    {"name": "reports:download", "description": "Descargar reportes generados"},
    {"name": "climate:manage", "description": "Configurar proyecciones climáticas downscaled"},
    {"name": "swat:manage", "description": "Configuración de cuenca y unidades de respuesta hidrológica (HRU)"},
]

INITIAL_ROLES = [
    {
        "name": "SUPERADMIN",
        "description": "Administrador total del sistema de gemelos digitales",
        "permissions": ["users:read", "users:write", "users:delete", "roles:read", "simulations:create", "simulations:read", "simulations:execute", "digital_twin:view_3d", "digital_twin:control", "reports:generate", "reports:download", "climate:manage", "swat:manage"]
    },
    {
        "name": "ADMIN_CIENTIFICO",
        "description": "Científico líder de modelado hidrológico y proyecciones climáticas",
        "permissions": ["users:read", "roles:read", "simulations:create", "simulations:read", "simulations:execute", "digital_twin:view_3d", "digital_twin:control", "reports:generate", "reports:download", "climate:manage", "swat:manage"]
    },
    {
        "name": "INVESTIGADOR_HIDROLOGO",
        "description": "Investigador enfocado en cuencas y análisis de escenarios sintéticos",
        "permissions": ["simulations:create", "simulations:read", "simulations:execute", "digital_twin:view_3d", "digital_twin:control", "reports:generate", "reports:download"]
    },
    {
        "name": "OPERADOR_AGROPECUARIO",
        "description": "Técnico u operador de campo monitoreando parcela y planta individual",
        "permissions": ["simulations:read", "digital_twin:view_3d", "reports:download"]
    },
    {
        "name": "LECTOR_AUDITOR",
        "description": "Acceso de solo lectura para auditorías y revisión de reportes",
        "permissions": ["simulations:read", "reports:download"]
    }
]

CLIMATE_SCENARIOS_DATA = [
    {
        "code": "HISTORICAL",
        "name": "Control sintético (sin anomalía)",
        "pathway": "Control sintético",
        "description": "Forzamiento estacional sintético para desarrollo; no contiene observaciones.",
        "temp_anomaly_c": 0.0,
        "precip_factor": 1.0,
        "co2_ppm": 395.0
    },
    {
        "code": "SSP1_26",
        "name": "Perturbación sintética inspirada en SSP1-2.6",
        "pathway": "Control de anomalía sintética",
        "description": "Control demostrativo; no utiliza datos CMIP6.",
        "temp_anomaly_c": 0.8,
        "precip_factor": 0.96,
        "co2_ppm": 440.0
    },
    {
        "code": "SSP2_45",
        "name": "Perturbación sintética inspirada en SSP2-4.5",
        "pathway": "Control de anomalía sintética",
        "description": "Control demostrativo; no utiliza datos CMIP6.",
        "temp_anomaly_c": 1.5,
        "precip_factor": 0.90,
        "co2_ppm": 540.0
    },
    {
        "code": "SSP5_85",
        "name": "Perturbación sintética inspirada en SSP5-8.5",
        "pathway": "Control de anomalía sintética",
        "description": "Control demostrativo de calentamiento y lluvia; no utiliza datos CMIP6.",
        "temp_anomaly_c": 3.2,
        "precip_factor": 0.82,
        "co2_ppm": 850.0
    }
]

async def bootstrap_system_reference_data(db: AsyncSession) -> None:
    """Create the structural RBAC catalog required in every environment."""
    existing_perms_res = await db.execute(select(Permission))
    existing_perms = {p.name: p for p in existing_perms_res.scalars().all()}

    for perm_data in INITIAL_PERMISSIONS:
        if perm_data["name"] not in existing_perms:
            p = Permission(name=perm_data["name"], description=perm_data["description"])
            db.add(p)
            existing_perms[perm_data["name"]] = p

    await db.flush()

    existing_roles_res = await db.execute(select(Role))
    existing_roles = {r.name: r for r in existing_roles_res.scalars().all()}

    for role_data in INITIAL_ROLES:
        role = existing_roles.get(role_data["name"])
        if not role:
            role = Role(name=role_data["name"], description=role_data["description"])
            db.add(role)
            existing_roles[role_data["name"]] = role
        role.description = role_data["description"]
        role.permissions = [existing_perms[pname] for pname in role_data["permissions"]]

    await db.commit()
    logger.info("Bootstrap RBAC completo: permisos y roles estructurales disponibles.")


async def seed_legacy_demo_data(db: AsyncSession) -> None:
    """Populate opt-in legacy-demo users, geography, scenarios, and simulation data."""
    existing_roles_res = await db.execute(select(Role))
    existing_roles = {r.name: r for r in existing_roles_res.scalars().all()}

    # Usuarios de prueba; never invoked by a non-demo startup.
    test_users = [
        {
            "email": "admin@digitaltwin.org",
            "password": "Admin123!",
            "full_name": "LEGACY DEMO — Dr. Carlos Valdivia (Superadmin)",
            "role": "SUPERADMIN",
            "institution": "Centro de Modelado Hidrológico y Cambio Climático",
            "specialty": "Ecohidrología y Gemelos Digitales"
        },
        {
            "email": "investigador@digitaltwin.org",
            "password": "Investiga123!",
            "full_name": "LEGACY DEMO — Dra. Elena Ramos (Investigadora)",
            "role": "INVESTIGADOR_HIDROLOGO",
            "institution": "Instituto Nacional del Agua",
            "specialty": "Modelación SWAT y Proyecciones Climáticas"
        },
        {
            "email": "operador@digitaltwin.org",
            "password": "Operador123!",
            "full_name": "LEGACY DEMO — Ing. Mateo Morales (Operador)",
            "role": "OPERADOR_AGROPECUARIO",
            "institution": "Distrito de Riego Cuenca Alta",
            "specialty": "Manejo Hídrico y Fisiología de Cultivos"
        }
    ]

    first_user_id = None
    for u_info in test_users:
        user_stmt = select(User).where(User.email == u_info["email"])
        user_res = await db.execute(user_stmt)
        user_obj = user_res.scalar_one_or_none()
        if not user_obj:
            target_role = existing_roles.get(u_info["role"])
            u = User(
                email=u_info["email"],
                hashed_password=hash_password(u_info["password"]),
                full_name=u_info["full_name"],
                is_active=True,
                is_verified=True,
                roles=[target_role] if target_role else []
            )
            db.add(u)
            await db.flush()

            prof = UserProfile(
                user_id=u.id,
                institution=u_info["institution"],
                scientific_specialty=u_info["specialty"],
                preferred_theme="scientific"
            )
            db.add(prof)
            if not first_user_id:
                first_user_id = u.id
        elif not first_user_id:
            first_user_id = user_obj.id

    await db.flush()

    # Especies de plantas legacy demo.
    crop_stmt = select(PlantSpecies).where(PlantSpecies.name.in_(["Palto Hass", "LEGACY DEMO — Palto Hass"]))
    crop_res = await db.execute(crop_stmt)
    hass_crop = crop_res.scalar_one_or_none()
    if not hass_crop:
        hass_crop = PlantSpecies(
            name="LEGACY DEMO — Palto Hass",
            scientific_name="Persea americana Mill.",
            crop_type="Frutal Arbóreo",
            base_kc=1.05,
            max_root_depth_cm=120.0,
            optimal_temp_c=24.0,
            stomatal_conductance_max=320.0
        )
        db.add(hass_crop)
        await db.flush()
    else:
        hass_crop.name = "LEGACY DEMO — Palto Hass"

    # Legacy demo watershed; it is not a verified research watershed.
    w_stmt = select(Watershed).where(Watershed.code == "CUENCA-SANTA-EULALIA")
    w_res = await db.execute(w_stmt)
    watershed = w_res.scalar_one_or_none()
    if not watershed:
        watershed = Watershed(
            code="CUENCA-SANTA-EULALIA",
            name="LEGACY DEMO — Santa Eulalia / Rímac",
            country="Perú",
            area_km2=420.5,
            elevation_min_m=850.0,
            elevation_max_m=4350.0,
            outlet_lat=-11.8902,
            outlet_lon=-76.6215,
            dem_metadata={
                "grid_size": [32, 32],
                "terrain_type": "mountainous_valley",
                "river_path": [
                    [-15, 0, -15], [-10, 0, -8], [-5, 0, -3],
                    [0, 0, 0], [6, 0, 5], [12, 0, 11], [18, 0, 16]
                ]
            }
        )
        db.add(watershed)
        await db.flush()

        # Crear Subcuencas
        sub1 = Subbasin(
            watershed_id=watershed.id,
            subbasin_number=1,
            name="Subcuenca Alta (Cabecera)",
            area_km2=180.2,
            mean_slope_percent=22.4,
            reach_length_km=18.5
        )
        sub2 = Subbasin(
            watershed_id=watershed.id,
            subbasin_number=2,
            name="Subcuenca Media (Valle Agrícola)",
            area_km2=165.0,
            mean_slope_percent=12.1,
            reach_length_km=14.2
        )
        sub3 = Subbasin(
            watershed_id=watershed.id,
            subbasin_number=3,
            name="Subcuenca Baja (Exutorio)",
            area_km2=75.3,
            mean_slope_percent=6.5,
            reach_length_km=9.8
        )
        db.add_all([sub1, sub2, sub3])
        await db.flush()

        # HRU Agrícola acoplada a la planta
        hru_agri = HRU(
            subbasin_id=sub2.id,
            hru_number=1,
            land_use="AGRICULTURAL_ORCHARD",
            soil_type="FRANCO_ARCILLOSO",
            curve_number_ii=74.0,
            area_fraction=0.45,
            plant_species_id=hass_crop.id
        )
        db.add(hru_agri)
        await db.flush()
    else:
        watershed.name = "LEGACY DEMO — Santa Eulalia / Rímac"

    # Escenarios sintéticos legacy demo.
    existing_scenarios_res = await db.execute(select(ClimateScenario))
    existing_scenarios = {s.code: s for s in existing_scenarios_res.scalars().all()}

    for s_data in CLIMATE_SCENARIOS_DATA:
        if s_data["code"] not in existing_scenarios:
            s_obj = ClimateScenario(**s_data, source_type="SYNTHETIC")
            db.add(s_obj)
            existing_scenarios[s_data["code"]] = s_obj
        else:
            # Repair legacy demo labels without changing identifiers or deleting runs.
            s_obj = existing_scenarios[s_data["code"]]
            for key, value in s_data.items():
                setattr(s_obj, key, value)
            s_obj.source_type = "SYNTHETIC"

    await db.flush()

    # Precomputed legacy-demo simulation for local UI development only.
    sim_check_stmt = select(SimulationRun).limit(1)
    sim_check = await db.execute(sim_check_stmt)
    if not sim_check.scalar_one_or_none() and first_user_id:
        target_scenario = existing_scenarios.get("SSP2_45") or list(existing_scenarios.values())[0]
        demo_sim = SimulationRun(
            user_id=first_user_id,
            watershed_id=watershed.id,
            scenario_id=target_scenario.id,
            name="LEGACY DEMO — clima sintético / planta representativa",
            status="PENDING",
            duration_days=365,
            irrigation_efficiency=None,
            seed=42,
            parameters={},
            requested_config={"duration_days": 365, "seed": 42, "parameters": {}, "evidence_type": "DEMO"},
        )
        db.add(demo_sim)
        await db.flush()

        # Ejecutar acoplamiento para generar resultados
        await TwinCouplingEngine.execute_simulation_run(db, demo_sim.id)

    await db.commit()
    logger.info("Seed DEMO completo: catálogo y forzamientos sintéticos listos.")


async def seed_initial_data(db: AsyncSession) -> None:
    """Compatibility entry point: bootstrap RBAC, then optionally add legacy demo fixtures."""
    await bootstrap_system_reference_data(db)
    if settings.ENABLE_DEMO_SEED:
        await seed_legacy_demo_data(db)
    else:
        logger.info("Legacy demo seed skipped because ENABLE_DEMO_SEED is false.")
