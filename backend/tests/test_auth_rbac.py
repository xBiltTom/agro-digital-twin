import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_login_superadmin_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/auth/login", json={
            "email": "admin@digitaltwin.org",
            "password": "Admin123!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "admin@digitaltwin.org"
        assert "SUPERADMIN" in data["user"]["roles"]

@pytest.mark.asyncio
async def test_login_invalid_credentials():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/auth/login", json={
            "email": "admin@digitaltwin.org",
            "password": "WrongPassword!"
        })
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user_me():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Login
        login_res = await ac.post("/api/v1/auth/login", json={
            "email": "investigador@digitaltwin.org",
            "password": "Investiga123!"
        })
        token = login_res.json()["access_token"]

        # Call /me
        me_res = await ac.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert me_res.status_code == 200
        data = me_res.json()
        assert data["email"] == "investigador@digitaltwin.org"
        assert any(r["name"] == "INVESTIGADOR_HIDROLOGO" for r in data["roles"])

@pytest.mark.asyncio
async def test_rbac_access_restrictions():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Operador intenta listar usuarios (requiere SUPERADMIN o ADMIN_CIENTIFICO)
        op_login = await ac.post("/api/v1/auth/login", json={
            "email": "operador@digitaltwin.org",
            "password": "Operador123!"
        })
        op_token = op_login.json()["access_token"]

        forbidden_res = await ac.get("/api/v1/users", headers={
            "Authorization": f"Bearer {op_token}"
        })
        assert forbidden_res.status_code == 403

        # 2. Superadmin accede a listar usuarios
        admin_login = await ac.post("/api/v1/auth/login", json={
            "email": "admin@digitaltwin.org",
            "password": "Admin123!"
        })
        admin_token = admin_login.json()["access_token"]

        allowed_res = await ac.get("/api/v1/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert allowed_res.status_code == 200
        users_list = allowed_res.json()
        assert len(users_list) >= 3

@pytest.mark.asyncio
async def test_register_new_user_and_profile_update():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        new_email = "nuevo_cientifico@digitaltwin.org"
        reg_res = await ac.post("/api/v1/auth/register", json={
            "email": new_email,
            "password": "Password123!",
            "full_name": "Dr. Fernando Morales",
            "institution": "Universidad Nacional de Ingeniería",
            "scientific_specialty": "Sensorica y Drones"
        })
        assert reg_res.status_code == 201

        # Login con el nuevo usuario
        login_res = await ac.post("/api/v1/auth/login", json={
            "email": new_email,
            "password": "Password123!"
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]

        # Actualizar perfil
        update_profile_res = await ac.put(
            "/api/v1/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "bio": "Investigador en ecohidrología cuantitativa",
                "preferred_theme": "dark"
            }
        )
        assert update_profile_res.status_code == 200
        profile_data = update_profile_res.json()
        assert profile_data["bio"] == "Investigador en ecohidrología cuantitativa"
        assert profile_data["preferred_theme"] == "dark"
