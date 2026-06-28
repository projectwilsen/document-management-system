import pytest


@pytest.mark.asyncio
async def test_register_creates_user_and_org(client):
    resp = await client.post("/auth/register", json={"email": "a@b.com", "password": "pass123", "name": "Org A"})
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_400(client):
    payload = {"email": "a@b.com", "password": "pass123", "name": "Org A"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_returns_tokens(client):
    await client.post("/auth/register", json={"email": "a@b.com", "password": "pass123", "name": "Org A"})
    resp = await client.post("/auth/login", json={"email": "a@b.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client):
    await client.post("/auth/register", json={"email": "a@b.com", "password": "pass123", "name": "Org A"})
    resp = await client.post("/auth/login", json={"email": "a@b.com", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_returns_new_tokens(client):
    reg = await client.post("/auth/register", json={"email": "a@b.com", "password": "pass123", "name": "Org A"})
    refresh_token = reg.json()["refresh_token"]
    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
