from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, board_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.rooms[board_id].add(websocket)

    def disconnect(self, board_id: int, websocket: WebSocket) -> None:
        room = self.rooms.get(board_id)
        if room is not None and websocket in room:
            room.remove(websocket)
        if room is not None and len(room) == 0:
            self.rooms.pop(board_id, None)

    async def broadcast(self, board_id: int, message: dict) -> None:
        for ws in list(self.rooms.get(board_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(board_id, ws)


manager = ConnectionManager()
