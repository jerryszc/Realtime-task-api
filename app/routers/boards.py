from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.board import BoardCreate, BoardRead
from app.schemas.task import TaskRead
from app.services import board_service, task_service

router = APIRouter(tags=["boards"])


@router.post("/boards", response_model=BoardRead, status_code=status.HTTP_201_CREATED)
def create_board(
    data: BoardCreate,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> BoardRead:
    return board_service.create_board(session, current.id, data)


@router.get("/workspaces/{workspace_id}/boards", response_model=list[BoardRead])
def list_boards(
    workspace_id: int,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[BoardRead]:
    return board_service.list_boards(session, current.id, workspace_id)


@router.get("/boards/{board_id}", response_model=BoardRead)
def get_board(
    board_id: int,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> BoardRead:
    return board_service.get_board(session, current.id, board_id)


@router.get("/boards/{board_id}/tasks", response_model=list[TaskRead])
def list_tasks(
    board_id: int,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[TaskRead]:
    return task_service.list_tasks(session, current.id, board_id)
