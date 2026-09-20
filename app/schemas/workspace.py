from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel

from app.models.workspace import WorkspaceRole


class WorkspaceCreate(SQLModel):
    name: str
    slug: str


class WorkspaceRead(SQLModel):
    id: int
    name: str
    slug: str
    owner_id: int
    created_at: datetime


class MemberAdd(SQLModel):
    user_id: int
    role: WorkspaceRole = WorkspaceRole.member


class MemberRead(SQLModel):
    workspace_id: int
    user_id: int
    role: WorkspaceRole
    joined_at: datetime


class MemberRoleUpdate(SQLModel):
    role: WorkspaceRole
