from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[str, set[WebSocket]] = defaultdict(set)

    @staticmethod
    def board_room(board_id: int) -> str:
        return f"board:{board_id}"

    @staticmethod
    def workspace_room(workspace_id: int) -> str:
        return f"workspace:{workspace_id}"

    async def connect_to_room(self, room: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.rooms[room].add(websocket)

    def disconnect_from_room(self, room: str, websocket: WebSocket) -> None:
        existing = self.rooms.get(room)
        if existing is not None and websocket in existing:
            existing.remove(websocket)
        if existing is not None and len(existing) == 0:
            self.rooms.pop(room, None)

    async def broadcast_to_room(self, room: str, message: dict[str, Any]) -> None:
        for ws in list(self.rooms.get(room, set())):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect_from_room(room, ws)

    async def connect(self, board_id: int, websocket: WebSocket) -> None:
        await self.connect_to_room(self.board_room(board_id), websocket)

    def disconnect(self, board_id: int, websocket: WebSocket) -> None:
        self.disconnect_from_room(self.board_room(board_id), websocket)

    async def broadcast(self, board_id: int, message: dict[str, Any]) -> None:
        await self.broadcast_to_room(self.board_room(board_id), message)

    async def connect_workspace(self, workspace_id: int, websocket: WebSocket) -> None:
        await self.connect_to_room(self.workspace_room(workspace_id), websocket)

    def disconnect_workspace(self, workspace_id: int, websocket: WebSocket) -> None:
        self.disconnect_from_room(self.workspace_room(workspace_id), websocket)

    async def broadcast_workspace(self, workspace_id: int, message: dict[str, Any]) -> None:
        await self.broadcast_to_room(self.workspace_room(workspace_id), message)

    def active_connections(self, room: str) -> int:
        return len(self.rooms.get(room, set()))


manager = ConnectionManager()
