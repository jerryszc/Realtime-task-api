from typing import cast

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.board import Board
from app.models.task import Task, TaskPriority, TaskStatus
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
) -> Board:
    return board_service.create_board(session, cast(int, current.id), data)


@router.get("/workspaces/{workspace_id}/boards", response_model=list[BoardRead])
def list_boards(
    workspace_id: int,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[Board]:
    return board_service.list_boards(session, cast(int, current.id), workspace_id)


@router.get("/boards/{board_id}", response_model=BoardRead)
def get_board(
    board_id: int,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Board:
    return board_service.get_board(session, cast(int, current.id), board_id)


@router.get("/boards/{board_id}/tasks", response_model=list[TaskRead])
def list_tasks(
    board_id: int,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status: TaskStatus | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
) -> list[Task]:
    return task_service.list_tasks(
        session, cast(int, current.id), board_id, skip, limit, status, priority
    )
