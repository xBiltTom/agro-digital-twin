"""
Role-Based Access Control (RBAC) & Permission Matrix for AgroTwin-AI.
Defines 4 distinct roles:
1. ADMIN: Complete system control, retraining, database configuration, user management.
2. RESEARCHER: Training pipeline execution, Sobol sensitivity, climate/management scenarios, report export.
3. ANALYST: Interactive inference, benchmarking evaluation, visualization, report export.
4. GUEST: Read-only exploratory access to pre-computed metrics and maps.
"""

from enum import Enum
from typing import Dict, Set


class Role(str, Enum):
    ADMIN = "ADMIN"
    RESEARCHER = "RESEARCHER"
    ANALYST = "ANALYST"
    GUEST = "GUEST"


class Permission(str, Enum):
    VIEW_EXPLORATION = "VIEW_EXPLORATION"
    VIEW_TWIN_SIMULATION = "VIEW_TWIN_SIMULATION"
    RUN_INFERENCE = "RUN_INFERENCE"
    RUN_BENCHMARKING = "RUN_BENCHMARKING"
    RUN_TRAINING = "RUN_TRAINING"
    RUN_SENSITIVITY = "RUN_SENSITIVITY"
    EXPORT_REPORTS = "EXPORT_REPORTS"
    MANAGE_SETTINGS = "MANAGE_SETTINGS"
    MANAGE_USERS = "MANAGE_USERS"


PERMISSION_MATRIX: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.VIEW_EXPLORATION,
        Permission.VIEW_TWIN_SIMULATION,
        Permission.RUN_INFERENCE,
        Permission.RUN_BENCHMARKING,
        Permission.RUN_TRAINING,
        Permission.RUN_SENSITIVITY,
        Permission.EXPORT_REPORTS,
        Permission.MANAGE_SETTINGS,
        Permission.MANAGE_USERS,
    },
    Role.RESEARCHER: {
        Permission.VIEW_EXPLORATION,
        Permission.VIEW_TWIN_SIMULATION,
        Permission.RUN_INFERENCE,
        Permission.RUN_BENCHMARKING,
        Permission.RUN_TRAINING,
        Permission.RUN_SENSITIVITY,
        Permission.EXPORT_REPORTS,
    },
    Role.ANALYST: {
        Permission.VIEW_EXPLORATION,
        Permission.VIEW_TWIN_SIMULATION,
        Permission.RUN_INFERENCE,
        Permission.RUN_BENCHMARKING,
        Permission.EXPORT_REPORTS,
    },
    Role.GUEST: {
        Permission.VIEW_EXPLORATION,
        Permission.VIEW_TWIN_SIMULATION,
        Permission.RUN_BENCHMARKING,
    }
}


def has_permission(role: Role, permission: Permission) -> bool:
    """Checks whether the given role has the requested permission."""
    allowed = PERMISSION_MATRIX.get(role, set())
    return permission in allowed


def get_role_description(role: Role) -> str:
    """Returns human-readable description and badge color for UI."""
    descriptions = {
        Role.ADMIN: ("Administrador de Sistema (Control total)", "#DC2626"),
        Role.RESEARCHER: ("Investigador Científico (Entrenamiento, Sobol, Escenarios)", "#2563EB"),
        Role.ANALYST: ("Analista Agronómico (Inferencia, Benchmarking, Exportación)", "#059669"),
        Role.GUEST: ("Invitado / Auditor (Modo sólo lectura)", "#6B7280")
    }
    return descriptions.get(role, ("Usuario", "#6B7280"))
