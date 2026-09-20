from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.core import security
from app.db.session import get_session
from app.models.board import Board
from app.models.workspace import WorkspaceMember
from app.services.ws_manager import manager

router = APIRouter(tags=["ws"])


def _can_access(session: Session, user_id: int, board_id: int) -> bool:
    board = session.get(Board, board_id)
    if board is None:
        return False
    member = session.get(WorkspaceMember, (board.workspace_id, user_id))
    return member is not None


@router.websocket("/ws/boards/{board_id}")
async def board_ws(
    websocket: WebSocket, board_id: int, token: str | None = None
) -> None:
    if token is None:
        await websocket.close(code=4401)
        return
    subject = security.decode_token(token, "access")
    if subject is None:
        await websocket.close(code=4401)
        return
    try:
        user_id = int(subject)
    except ValueError:
        await websocket.close(code=4401)
        return
    for session in get_session():
        if not _can_access(session, user_id, board_id):
            await websocket.close(code=4403)
            return
    await manager.connect(board_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(board_id, websocket)
