"""Auth flow: signup → login → me."""

from __future__ import annotations

from httpx import AsyncClient

EMAIL = "alice@example.com"
PASSWORD = "correct horse battery staple"


async def test_signup_login_me(client: AsyncClient) -> None:
    # Signup
    r = await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]

    # Duplicate signup → 409
    r = await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 409

    # Login
    r = await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200
    access = r.json()["access_token"]

    # Me
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["email"] == EMAIL


async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    r = await client.post("/api/auth/login", json={"email": EMAIL, "password": "nope nope nope"})
    assert r.status_code == 401
