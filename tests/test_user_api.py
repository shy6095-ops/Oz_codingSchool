from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import utcnow
from app.core.config import settings
from app.models.auth_token import RefreshSession
from app.models.user import Department, Gender, Role, User
from app.schemas.user import UserSignupRequest
from app.services.user_service import bootstrap_admin, create_user


def valid_signup(**overrides) -> dict:
    payload = {
        "email": "staff@example.com",
        "password": "Aa1!secure",
        "name": "홍길동",
        "department": "DEV",
        "gender": "M",
        "phone_number": "01012345678",
    }
    payload.update(overrides)
    return payload


async def login(client, email: str = "staff@example.com", password: str = "Aa1!secure"):
    return await client.post("/api/v1/users/login", data={"username": email, "password": password})


@pytest.mark.asyncio
async def test_signup_login_refresh_and_get_me(client):
    signup = await client.post("/api/v1/users/signup", json=valid_signup())
    assert signup.status_code == 201
    assert signup.json()["role"] == "PENDING"

    login_response = await login(client)
    assert login_response.status_code == 200
    assert "refresh_token" in login_response.headers["set-cookie"]
    access_token = login_response.json()["access_token"]

    me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "staff@example.com"

    refresh = await client.post("/api/v1/users/refresh")
    assert refresh.status_code == 200
    assert refresh.json()["access_token"] != access_token


@pytest.mark.asyncio
async def test_duplicate_signup_and_partial_profile_update(client):
    assert (await client.post("/api/v1/users/signup", json=valid_signup())).status_code == 201
    assert (await client.post("/api/v1/users/signup", json=valid_signup())).status_code == 409
    access_token = (await login(client)).json()["access_token"]

    updated = await client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"department": "RESEARCH"},
    )
    assert updated.status_code == 200
    assert updated.json()["department"] == "RESEARCH"


@pytest.mark.asyncio
async def test_password_change_requires_current_password(client):
    await client.post("/api/v1/users/signup", json=valid_signup())
    access_token = (await login(client)).json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    rejected = await client.patch(
        "/api/v1/users/me/password",
        headers=headers,
        json={"current_password": "wrong", "new_password": "Bb2!secure"},
    )
    assert rejected.status_code == 400

    changed = await client.patch(
        "/api/v1/users/me/password",
        headers=headers,
        json={"current_password": "Aa1!secure", "new_password": "Bb2!secure"},
    )
    assert changed.status_code == 204
    assert (await login(client, password="Bb2!secure")).status_code == 200


@pytest.mark.asyncio
async def test_logout_revokes_access_immediately(client):
    await client.post("/api/v1/users/signup", json=valid_signup())
    access_token = (await login(client)).json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    assert (await client.post("/api/v1/users/logout", headers=headers)).status_code == 204
    assert (await client.get("/api/v1/users/me", headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_delete_me_removes_user_and_refresh_sessions(client, session_factory):
    await client.post("/api/v1/users/signup", json=valid_signup())
    access_token = (await login(client)).json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    assert (await client.delete("/api/v1/users/me", headers=headers)).status_code == 204
    assert (await client.get("/api/v1/users/me", headers=headers)).status_code == 401
    async with session_factory() as session:
        assert list(await session.scalars(select(RefreshSession))) == []


@pytest.mark.asyncio
async def test_admin_filters_and_changes_selected_roles(client, session_factory):
    async with session_factory() as session:
        admin = await create_user(
            session,
            UserSignupRequest(**valid_signup(email="admin@example.com", phone_number="01099998888")),
            role=Role.ADMIN,
        )
    await client.post("/api/v1/users/signup", json=valid_signup())
    admin_token = (await login(client, "admin@example.com")).json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    listed = await client.get("/api/v1/admin/users", headers=headers, params={"department": "DEV", "query": "staff"})
    assert listed.status_code == 200
    assert [user["email"] for user in listed.json()] == ["staff@example.com"]

    updated = await client.patch(
        "/api/v1/admin/users/roles",
        headers=headers,
        json={"user_ids": [2], "role": "STAFF"},
    )
    assert updated.status_code == 200
    assert updated.json()[0]["role"] == "STAFF"


@pytest.mark.asyncio
async def test_bootstrap_admin_uses_only_configured_environment(session_factory, monkeypatch):
    configured_values = {
        "BOOTSTRAP_ADMIN_EMAIL": "bootstrap@example.com",
        "BOOTSTRAP_ADMIN_PASSWORD": "Aa1!secure",
        "BOOTSTRAP_ADMIN_NAME": "초기관리자",
        "BOOTSTRAP_ADMIN_PHONE_NUMBER": "01055556666",
        "BOOTSTRAP_ADMIN_DEPARTMENT": "DEV",
        "BOOTSTRAP_ADMIN_GENDER": "M",
    }
    for key, value in configured_values.items():
        monkeypatch.setattr(settings, key, value)

    async with session_factory() as session:
        await bootstrap_admin(session)
        await bootstrap_admin(session)
        admins = list(await session.scalars(select(User).where(User.role == Role.ADMIN)))

    assert [admin.email for admin in admins] == ["bootstrap@example.com"]
