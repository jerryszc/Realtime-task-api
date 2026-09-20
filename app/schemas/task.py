from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel

from app.models.task import TaskPriority, TaskStatus


class TaskCreate(SQLModel):
    board_id: int
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.medium
    position: float = 0.0
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None


class TaskUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    position: Optional[float] = None
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None


class TaskMove(SQLModel):
    status: Optional[TaskStatus] = None
    position: Optional[float] = None


class TaskRead(SQLModel):
    id: int
    board_id: int
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: TaskPriority
    position: float
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
