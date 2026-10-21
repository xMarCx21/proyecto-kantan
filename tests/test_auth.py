"""Pruebas unitarias y de integración para la autenticación y configuración base."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Verifica que el endpoint de salud responda 200 OK."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "Keyoku" in data["app"]


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    """Verifica el registro exitoso de un profesor."""
    payload = {
        "email": "profesor@colegio.edu",
        "password": "PasswordSegura123!",
        "full_name": "Profesor Juan Pérez",
        "school": "Colegio San Martín",
        "subject": "Matemáticas",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Verifica que no se permita registrar dos veces el mismo correo."""
    payload = {
        "email": "duplicado@colegio.edu",
        "password": "PasswordSegura123!",
        "full_name": "Profe Uno",
    }
    # Primer registro
    res1 = await client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    # Segundo registro con el mismo correo
    res2 = await client.post("/api/auth/register", json=payload)
    assert res2.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Verifica el login con credenciales correctas."""
    # 1. Registrar
    reg_payload = {
        "email": "login_test@colegio.edu",
        "password": "PasswordSegura123!",
        "full_name": "Profe Login",
    }
    await client.post("/api/auth/register", json=reg_payload)

    # 2. Login
    login_payload = {
        "email": "login_test@colegio.edu",
        "password": "PasswordSegura123!",
    }
    response = await client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    """Verifica que el login falle con contraseña errónea."""
    # 1. Registrar
    reg_payload = {
        "email": "wrong_pass@colegio.edu",
        "password": "PasswordCorrecta123!",
        "full_name": "Profe Wrong",
    }
    await client.post("/api/auth/register", json=reg_payload)

    # 2. Login con password incorrecto
    login_payload = {
        "email": "wrong_pass@colegio.edu",
        "password": "PasswordIncorrecta999!",
    }
    response = await client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient):
    """Verifica que /api/auth/me retorne los datos del usuario logueado con Bearer token."""
    reg_payload = {
        "email": "perfil@colegio.edu",
        "password": "PasswordSegura123!",
        "full_name": "María González",
        "school": "Instituto Sarmiento",
        "subject": "Ciencias Naturales",
    }
    reg_res = await client.post("/api/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["email"] == "perfil@colegio.edu"
    assert user_data["full_name"] == "María González"
    assert user_data["school"] == "Instituto Sarmiento"
    assert user_data["subject"] == "Ciencias Naturales"
    assert user_data["is_active"] is True
