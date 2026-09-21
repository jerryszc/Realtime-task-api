import pytest
from fastapi.testclient import TestClient

from app.services.ws_manager import ConnectionManager


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.sent: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict) -> None:
        self.sent.append(message)


@pytest.mark.anyio
async def test_manager_board_and_workspace_rooms() -> None:
    manager = ConnectionManager()
    ws1, ws2 = FakeWebSocket(), FakeWebSocket()
    await manager.connect(1, ws1)
    await manager.connect_workspace(7, ws2)

    await manager.broadcast(1, {"event": "task.created"})
    await manager.broadcast_workspace(7, {"event": "task.created"})

    assert ws1.sent == [{"event": "task.created"}]
    assert ws2.sent == [{"event": "task.created"}]
    assert manager.active_connections(manager.board_room(1)) == 1

    manager.disconnect(1, ws1)
    assert manager.active_connections(manager.board_room(1)) == 0


def test_ws_rejects_missing_token(client: TestClient) -> None:
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/boards/1"):
            pass


def test_ws_rejects_invalid_token(client: TestClient) -> None:
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/workspaces/1?token=invalid"):
            pass
