from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class BoardCreate(SQLModel):
    workspace_id: int
    title: str
    description: Optional[str] = None


class BoardRead(SQLModel):
    id: int
    workspace_id: int
    title: str
    description: Optional[str] = None
    created_at: datetime
