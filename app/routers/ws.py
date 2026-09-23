from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.core import security
from app.db.session import get_session
from app.models.board import Board
from app.models.workspace import Workspace, WorkspaceMember
from app.services.ws_manager import manager

router = APIRouter(tags=["ws"])


def _decode_user_id(token: str | None) -> int | None:
    if token is None:
        return None
    subject = security.decode_token(token, "access")
    if subject is None:
        return None
    try:
        return int(subject)
    except ValueError:
        return None


def _can_access_board(session: Session, user_id: int, board_id: int) -> bool:
    board = session.get(Board, board_id)
    if board is None:
        return False
    member = session.get(WorkspaceMember, (board.workspace_id, user_id))
    return member is not None


def _can_access_workspace(session: Session, user_id: int, workspace_id: int) -> bool:
    ws = session.get(Workspace, workspace_id)
    if ws is None:
        return False
    member = session.get(WorkspaceMember, (workspace_id, user_id))
    return member is not None


@router.websocket("/ws/boards/{board_id}")
async def board_ws(websocket: WebSocket, board_id: int, token: str | None = None) -> None:
    user_id = _decode_user_id(token)
    if user_id is None:
        await websocket.close(code=4401)
        return
    for session in get_session():
        if not _can_access_board(session, user_id, board_id):
            await websocket.close(code=4403)
            return
    await manager.connect(board_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(board_id, websocket)


@router.websocket("/ws/workspaces/{workspace_id}")
async def workspace_ws(websocket: WebSocket, workspace_id: int, token: str | None = None) -> None:
    user_id = _decode_user_id(token)
    if user_id is None:
        await websocket.close(code=4401)
        return
    for session in get_session():
        if not _can_access_workspace(session, user_id, workspace_id):
            await websocket.close(code=4403)
            return
    await manager.connect_workspace(workspace_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_workspace(workspace_id, websocket)
