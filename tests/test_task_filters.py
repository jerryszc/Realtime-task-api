from fastapi.testclient import TestClient


def _setup_board(client: TestClient) -> tuple[dict[str, str], int]:
    client.post(
        "/auth/register",
        json={"email": "f@example.com", "password": "secret123", "full_name": "F"},
    )
    token = client.post(
        "/auth/login", json={"email": "f@example.com", "password": "secret123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ws_id = client.post(
        "/workspaces", json={"name": "WF", "slug": "w-filters"}, headers=headers
    ).json()["id"]
    board_id = client.post(
        "/boards", json={"workspace_id": ws_id, "title": "B"}, headers=headers
    ).json()["id"]
    return headers, board_id


def test_pagination_and_filters(client: TestClient) -> None:
    headers, board_id = _setup_board(client)
    for i in range(5):
        res = client.post(
            "/tasks",
            json={
                "board_id": board_id,
                "title": f"T{i}",
                "priority": "high" if i % 2 == 0 else "low",
            },
            headers=headers,
        )
        assert res.status_code == 201
    first = client.get(f"/boards/{board_id}/tasks", headers=headers).json()[0]
    client.post(
        f"/tasks/{first['id']}/move",
        json={"status": "done", "position": 99.0},
        headers=headers,
    )

    page = client.get(f"/boards/{board_id}/tasks?skip=0&limit=2", headers=headers)
    assert page.status_code == 200
    assert len(page.json()) == 2

    done = client.get(f"/boards/{board_id}/tasks?status=done", headers=headers)
    assert done.status_code == 200
    assert len(done.json()) == 1
    assert done.json()[0]["status"] == "done"

    high = client.get(f"/boards/{board_id}/tasks?priority=high", headers=headers)
    assert high.status_code == 200
    assert all(t["priority"] == "high" for t in high.json())


def test_invalid_enum_rejected_422(client: TestClient) -> None:
    headers, board_id = _setup_board(client)
    bad_priority = client.post(
        "/tasks",
        json={"board_id": board_id, "title": "Bad", "priority": "urgent"},
        headers=headers,
    )
    assert bad_priority.status_code == 422

    bad_status = client.get(f"/boards/{board_id}/tasks?status=archived", headers=headers)
    assert bad_status.status_code == 422
