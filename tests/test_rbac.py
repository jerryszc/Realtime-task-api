from fastapi.testclient import TestClient


def _register_login(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/auth/register",
        json={"email": email, "password": "secret123", "full_name": email},
    )
    login = client.post("/auth/login", json={"email": email, "password": "secret123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_member_rbac_admin_only(client: TestClient) -> None:
    owner_h = _register_login(client, "owner@example.com")
    member_h = _register_login(client, "member@example.com")
    outsider_h = _register_login(client, "outsider@example.com")

    ws = client.post(
        "/workspaces", json={"name": "W", "slug": "w-rbac"}, headers=owner_h
    )
    assert ws.status_code == 201
    ws_id = ws.json()["id"]
    member_id = client.get("/auth/me", headers=member_h).json()["id"]

    add = client.post(
        f"/workspaces/{ws_id}/members",
        json={"user_id": member_id, "role": "member"},
        headers=owner_h,
    )
    assert add.status_code == 201

    outsider_id = client.get("/auth/me", headers=outsider_h).json()["id"]
    forbidden = client.post(
        f"/workspaces/{ws_id}/members",
        json={"user_id": outsider_id, "role": "member"},
        headers=member_h,
    )
    assert forbidden.status_code == 403

    board_forbidden = client.post(
        "/boards", json={"workspace_id": ws_id, "title": "X"}, headers=member_h
    )
    assert board_forbidden.status_code == 403

    board_ok = client.post(
        "/boards", json={"workspace_id": ws_id, "title": "Y"}, headers=owner_h
    )
    assert board_ok.status_code == 201

    no_access = client.get(f"/workspaces/{ws_id}/boards", headers=outsider_h)
    assert no_access.status_code in (403, 404)
