from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.board import Board
from app.models.task import Task, TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskMove, TaskUpdate
from app.services.workspace_service import require_membership


def _get_board_or_404(session: Session, board_id: int) -> Board:
    board = session.get(Board, board_id)
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return board


def create_task(session: Session, user_id: int, data: TaskCreate) -> Task:
    board = _get_board_or_404(session, data.board_id)
    require_membership(session, board.workspace_id, user_id)
    try:
        task = Task(
            board_id=data.board_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            position=data.position,
            assignee_id=data.assignee_id,
            due_date=data.due_date,
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        return task
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create task"
        )


def list_tasks(
    session: Session,
    user_id: int,
    board_id: int,
    skip: int = 0,
    limit: int = 50,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
) -> list[Task]:
    board = _get_board_or_404(session, board_id)
    require_membership(session, board.workspace_id, user_id)
    query = select(Task).where(Task.board_id == board_id)
    if status is not None:
        query = query.where(Task.status == status)
    if priority is not None:
        query = query.where(Task.priority == priority)
    query = query.order_by(Task.position).offset(skip).limit(limit)
    return list(session.exec(query).all())


def update_task(session: Session, user_id: int, task_id: int, data: TaskUpdate) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    board = _get_board_or_404(session, task.board_id)
    require_membership(session, board.workspace_id, user_id)
    try:
        payload = data.model_dump(exclude_unset=True)
        for key, value in payload.items():
            setattr(task, key, value)
        task.updated_at = datetime.utcnow()
        session.add(task)
        session.commit()
        session.refresh(task)
        return task
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update task"
        )


def move_task(session: Session, user_id: int, task_id: int, data: TaskMove) -> Task:
    payload = TaskUpdate(
        status=data.status, position=data.position if data.position is not None else None
    )
    filtered = TaskUpdate(
        **{k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    )
    return update_task(session, user_id, task_id, filtered)


def delete_task(session: Session, user_id: int, task_id: int) -> None:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    board = _get_board_or_404(session, task.board_id)
    require_membership(session, board.workspace_id, user_id)
    try:
        session.delete(task)
        session.commit()
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete task"
        )
