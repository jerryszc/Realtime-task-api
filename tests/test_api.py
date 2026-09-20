from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_register_login_refresh(client: TestClient) -> None:
    reg = client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "secret123", "full_name": "User A"},
    )
    assert reg.status_code == 201

    login = client.post(
        "/auth/login", json={"email": "a@example.com", "password": "secret123"}
    )
    assert login.status_code == 200
    tokens = login.json()
    assert "access_token" in tokens and "refresh_token" in tokens

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"

    refreshed = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert "access_token" in refreshed.json()


def test_workspace_board_task_flow(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": "b@example.com", "password": "secret123", "full_name": "User B"},
    )
    login = client.post("/auth/login", json={"email": "b@example.com", "password": "secret123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = client.post(
        "/workspaces", json={"name": "Team", "slug": "team"}, headers=headers
    )
    assert ws.status_code == 201
    ws_id = ws.json()["id"]

    board = client.post(
        "/boards",
        json={"workspace_id": ws_id, "title": "Sprint 1"},
        headers=headers,
    )
    assert board.status_code == 201
    board_id = board.json()["id"]

    task = client.post(
        "/tasks", json={"board_id": board_id, "title": "Task 1"}, headers=headers
    )
    assert task.status_code == 201
    task_id = task.json()["id"]
    assert task.json()["status"] == "todo"

    moved = client.post(
        f"/tasks/{task_id}/move",
        json={"status": "in_progress", "position": 1.0},
        headers=headers,
    )
    assert moved.status_code == 200
    assert moved.json()["status"] == "in_progress"
