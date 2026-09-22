from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.board import Board
    from app.models.user import User


class TaskStatus(StrEnum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TaskPriority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    board_id: int = Field(foreign_key="board.id", index=True)
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)
    status: TaskStatus = Field(default=TaskStatus.todo, index=True)
    priority: TaskPriority = Field(default=TaskPriority.medium)
    position: float = Field(default=0.0)
    assignee_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    due_date: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    board: Optional["Board"] = Relationship(back_populates="tasks")
    assignee: Optional["User"] = Relationship(back_populates="assigned_tasks")
