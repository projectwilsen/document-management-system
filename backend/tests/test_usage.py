import pytest


async def _auth_header(client):
    r = await client.post("/auth/register", json={"email": "a@b.com", "password": "pass123", "name": "Org"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_quota_returns_remaining(client):
    headers = await _auth_header(client)
    resp = await client.get("/usage/quota", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["remaining"] == 50


@pytest.mark.asyncio
async def test_report_decrements_quota(client):
    headers = await _auth_header(client)
    await client.post("/usage/report", json={"files_processed": 10}, headers=headers)
    resp = await client.get("/usage/quota", headers=headers)
    assert resp.json()["remaining"] == 40
    assert resp.json()["used"] == 10


@pytest.mark.asyncio
async def test_report_blocks_when_quota_exceeded(client):
    headers = await _auth_header(client)
    await client.post("/usage/report", json={"files_processed": 50}, headers=headers)
    resp = await client.post("/usage/report", json={"files_processed": 1}, headers=headers)
    assert resp.status_code == 402
