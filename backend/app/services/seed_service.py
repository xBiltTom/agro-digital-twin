import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.security import hash_password
from backend.app.models.user import User, Role, Permission, UserProfile

logger = logging.getLogger(__name__)

INITIAL_PERMISSIONS = [
    {"name": "users:read", "description": "Consultar lista y detalle de usuarios"},
    {"name": "users:write", "description": "Crear y actualizar usuarios"},
    {"name": "users:delete", "description": "Desactivar usuarios del sistema"},
    {"name": "roles:read", "description": "Consultar roles y permisos"},
    {"name": "simulations:create", "description": "Crear nuevos experimentos de simulación SWAT"},
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
        "description": "Investigador enfocado en cuencas, calibración SWAT y análisis de escenarios",
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

async def seed_initial_data(db: AsyncSession) -> None:
    """Poblar permisos, roles y usuarios iniciales si no existen."""
    # 1. Permisos
    existing_perms_res = await db.execute(select(Permission))
    existing_perms = {p.name: p for p in existing_perms_res.scalars().all()}

    for perm_data in INITIAL_PERMISSIONS:
        if perm_data["name"] not in existing_perms:
            p = Permission(name=perm_data["name"], description=perm_data["description"])
            db.add(p)
            existing_perms[perm_data["name"]] = p

    await db.flush()

    # 2. Roles
    existing_roles_res = await db.execute(select(Role))
    existing_roles = {r.name: r for r in existing_roles_res.scalars().all()}

    for role_data in INITIAL_ROLES:
        if role_data["name"] not in existing_roles:
            r = Role(name=role_data["name"], description=role_data["description"])
            # Asignar permisos
            role_perms = [existing_perms[pname] for pname in role_data["permissions"] if pname in existing_perms]
            r.permissions = role_perms
            db.add(r)
            existing_roles[role_data["name"]] = r

    await db.flush()

    # 3. Usuarios de prueba
    test_users = [
        {
            "email": "admin@digitaltwin.org",
            "password": "Admin123!",
            "full_name": "Dr. Carlos Valdivia (Superadmin)",
            "role": "SUPERADMIN",
            "institution": "Centro de Modelado Hidrológico y Cambio Climático",
            "specialty": "Ecohidrología y Gemelos Digitales"
        },
        {
            "email": "investigador@digitaltwin.org",
            "password": "Investiga123!",
            "full_name": "Dra. Elena Ramos (Investigadora SWAT)",
            "role": "INVESTIGADOR_HIDROLOGO",
            "institution": "Instituto Nacional del Agua",
            "specialty": "Modelación SWAT y Proyecciones Climáticas"
        },
        {
            "email": "operador@digitaltwin.org",
            "password": "Operador123!",
            "full_name": "Ing. Mateo Morales (Agrónomo de Campo)",
            "role": "OPERADOR_AGROPECUARIO",
            "institution": "Distrito de Riego Cuenca Alta",
            "specialty": "Manejo Hídrico y Fisiología de Cultivos"
        }
    ]

    for u_info in test_users:
        user_stmt = select(User).where(User.email == u_info["email"])
        user_res = await db.execute(user_stmt)
        if not user_res.scalar_one_or_none():
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

    await db.commit()
    logger.info("Seed completado exitosamente: Roles, permisos y usuarios iniciales listos.")
