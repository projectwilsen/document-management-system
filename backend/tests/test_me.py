import pytest


async def _register_and_token(client, email="a@b.com"):
    r = await client.post("/auth/register", json={"email": email, "password": "pass123", "name": "Org"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_me_returns_profile_and_quota(client):
    token = await _register_and_token(client)
    resp = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "a@b.com"
    assert data["plan"] == "free"
    assert data["quota"]["limit"] == 50
    assert data["quota"]["used"] == 0
    assert data["quota"]["remaining"] == 50


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/me")
    assert resp.status_code == 403
