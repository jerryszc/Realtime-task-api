from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.board import Board
from app.models.workspace import WorkspaceRole
from app.schemas.board import BoardCreate
from app.services.workspace_service import require_membership, require_role


def create_board(session: Session, user_id: int, data: BoardCreate) -> Board:
    require_role(session, data.workspace_id, user_id, [WorkspaceRole.owner, WorkspaceRole.admin])
    try:
        board = Board(
            workspace_id=data.workspace_id, title=data.title, description=data.description
        )
        session.add(board)
        session.commit()
        session.refresh(board)
        return board
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create board"
        ) from None


def list_boards(session: Session, user_id: int, workspace_id: int) -> list[Board]:
    require_membership(session, workspace_id, user_id)
    return list(session.exec(select(Board).where(Board.workspace_id == workspace_id)).all())


def get_board(session: Session, user_id: int, board_id: int) -> Board:
    board = session.get(Board, board_id)
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    require_membership(session, board.workspace_id, user_id)
    return board
