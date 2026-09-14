"""
Authentication Service with bcrypt password hashing for AgroTwin-AI.
Supports pre-configured user credentials for the 4 roles:
- admin      / Admin123!     -> ADMIN
- researcher / Research123!  -> RESEARCHER
- analyst    / Analyst123!   -> ANALYST
- guest      / Guest123!     -> GUEST
"""

import hashlib
from typing import Optional, Dict, Any
from dataclasses import dataclass
from .permissions import Role, Permission, has_permission

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False


@dataclass
class AuthenticatedUser:
    username: str
    email: str
    role: Role
    full_name: str

    def can(self, permission: Permission) -> bool:
        return has_permission(self.role, permission)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt (or sha256 fallback)."""
    if HAS_BCRYPT:
        salt = bcrypt.gensalt(rounds=10)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    else:
        # Fallback
        return "sha256$" + hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a hashed string."""
    if hashed_password.startswith("sha256$"):
        expected = "sha256$" + hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        return expected == hashed_password

    if HAS_BCRYPT:
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False

    return False


# Pre-seeded accounts (password hashes generated or verified on load)
SEED_USERS: Dict[str, Dict[str, Any]] = {
    "admin": {
        "email": "admin@agrotwin-lab.edu",
        "full_name": "Ing. Administrador de Plataforma",
        "role": Role.ADMIN,
        "password_hash": hash_password("Admin123!")
    },
    "researcher": {
        "email": "lead.researcher@agrotwin-lab.edu",
        "full_name": "Dr. Investigador Principal (Maíz / SWAT+)",
        "role": Role.RESEARCHER,
        "password_hash": hash_password("Research123!")
    },
    "analyst": {
        "email": "analyst@agrotwin-lab.edu",
        "full_name": "M.Sc. Analista de Cuencas Hidrológicas",
        "role": Role.ANALYST,
        "password_hash": hash_password("Analyst123!")
    },
    "guest": {
        "email": "guest@agrotwin-lab.edu",
        "full_name": "Visitante Académico (Solo Lectura)",
        "role": Role.GUEST,
        "password_hash": hash_password("Guest123!")
    }
}


class AuthService:
    """Authentication and session management provider."""

    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional[AuthenticatedUser]:
        """Validates credentials and returns AuthenticatedUser or None."""
        u_clean = username.strip().lower()
        user_info = SEED_USERS.get(u_clean)
        if not user_info:
            return None

        if verify_password(password, user_info["password_hash"]):
            return AuthenticatedUser(
                username=u_clean,
                email=user_info["email"],
                role=user_info["role"],
                full_name=user_info["full_name"]
            )
        return None

    @classmethod
    def get_default_guest(cls) -> AuthenticatedUser:
        """Returns the default unauthenticated guest identity."""
        u = SEED_USERS["guest"]
        return AuthenticatedUser(
            username="guest",
            email=u["email"],
            role=Role.GUEST,
            full_name=u["full_name"]
        )
