import pytest


async def _register(client, email, name="Org"):
    r = await client.post("/auth/register", json={"email": email, "password": "pass123", "name": name})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_list_users_returns_org_members(client):
    token = await _register(client, "owner@b.com")
    resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) == 1
    assert users[0]["email"] == "owner@b.com"
    assert users[0]["role"] == "owner"


@pytest.mark.asyncio
async def test_invite_returns_url(client):
    token = await _register(client, "owner@b.com")
    resp = await client.post("/admin/users/invite", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "invite_url" in resp.json()
    assert "/register?invite=" in resp.json()["invite_url"]


@pytest.mark.asyncio
async def test_member_cannot_access_admin(client):
    owner_token = await _register(client, "owner@b.com")
    invite_resp = await client.post("/admin/users/invite", headers={"Authorization": f"Bearer {owner_token}"})
    invite_url = invite_resp.json()["invite_url"]
    invite_param = invite_url.split("invite=")[1]

    member_r = await client.post(
        f"/auth/register?invite={invite_param}",
        json={"email": "member@b.com", "password": "pass123"},
    )
    member_token = member_r.json()["access_token"]

    resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {member_token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_remove_member(client):
    owner_token = await _register(client, "owner@b.com")
    invite_resp = await client.post("/admin/users/invite", headers={"Authorization": f"Bearer {owner_token}"})
    invite_param = invite_resp.json()["invite_url"].split("invite=")[1]

    member_r = await client.post(
        f"/auth/register?invite={invite_param}",
        json={"email": "member@b.com", "password": "pass123"},
    )
    member_id = (await client.get("/me", headers={"Authorization": f"Bearer {member_r.json()['access_token']}"})).json()["id"]

    resp = await client.delete(f"/admin/users/{member_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 204
