from typing import cast

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.board import Board
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskMove, TaskRead, TaskUpdate
from app.services import task_service
from app.services.ws_manager import manager

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _notify(session: Session, board_id: int, event: str, task_id: int | None = None) -> None:
    message = {"event": event, "board_id": board_id, "task_id": task_id}
    await manager.broadcast(board_id, message)
    board = session.get(Board, board_id)
    if board is not None:
        await manager.broadcast_workspace(
            board.workspace_id, {**message, "workspace_id": board.workspace_id}
        )


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Task:
    # response_model=TaskRead still drives serialization; the annotation mirrors
    # the ORM object actually returned (same convention as routers/auth.py).
    task = task_service.create_task(session, cast(int, current.id), data)
    await _notify(session, task.board_id, "task.created", task.id)
    return task


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Task:
    task = task_service.update_task(session, cast(int, current.id), task_id, data)
    await _notify(session, task.board_id, "task.updated", task.id)
    return task


@router.post("/{task_id}/move", response_model=TaskRead)
async def move_task(
    task_id: int,
    data: TaskMove,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Task:
    task = task_service.move_task(session, cast(int, current.id), task_id, data)
    await _notify(session, task.board_id, "task.moved", task.id)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    task = session.get(Task, task_id)
    board_id = task.board_id if task is not None else None
    task_service.delete_task(session, cast(int, current.id), task_id)
    if board_id is not None:
        await _notify(session, board_id, "task.deleted", task_id)
    return None
