"""
Tests for Auth Service, Roles/Permissions, and SQLAlchemy Database Fallback.
"""

import pytest
from src.infrastructure.auth import (
    AuthService,
    Role,
    Permission,
    has_permission,
    hash_password,
    verify_password
)
from src.infrastructure.database.connection import get_engine, init_db, get_session_factory, UserORM


def test_password_hashing_and_verification():
    plain = "SecureTestPassword123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_role_permission_matrix():
    # Admin can do everything
    assert has_permission(Role.ADMIN, Permission.RUN_TRAINING) is True
    assert has_permission(Role.ADMIN, Permission.MANAGE_USERS) is True

    # Researcher can train & export, but cannot manage users
    assert has_permission(Role.RESEARCHER, Permission.RUN_TRAINING) is True
    assert has_permission(Role.RESEARCHER, Permission.MANAGE_USERS) is False

    # Analyst can infer & export, but cannot train
    assert has_permission(Role.ANALYST, Permission.RUN_INFERENCE) is True
    assert has_permission(Role.ANALYST, Permission.RUN_TRAINING) is False

    # Guest can only explore and view benchmarks
    assert has_permission(Role.GUEST, Permission.VIEW_EXPLORATION) is True
    assert has_permission(Role.GUEST, Permission.RUN_TRAINING) is False
    assert has_permission(Role.GUEST, Permission.EXPORT_REPORTS) is False


def test_auth_service_preseeded_logins():
    # Valid credentials
    admin_user = AuthService.authenticate("admin", "Admin123!")
    assert admin_user is not None
    assert admin_user.role == Role.ADMIN
    assert admin_user.can(Permission.RUN_TRAINING) is True

    researcher = AuthService.authenticate("researcher", "Research123!")
    assert researcher is not None
    assert researcher.role == Role.RESEARCHER

    # Invalid password
    bad_login = AuthService.authenticate("admin", "WrongPass")
    assert bad_login is None

    # Unknown username
    unknown = AuthService.authenticate("nonexistent", "Pass123!")
    assert unknown is None


def test_database_init_and_sqlite_fallback():
    init_db()
    engine = get_engine()
    assert engine is not None

    factory = get_session_factory()
    with factory() as session:
        # Check users table can be queried
        count = session.query(UserORM).count()
        assert count >= 0
