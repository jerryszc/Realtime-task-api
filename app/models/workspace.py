from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.board import Board
    from app.models.user import User


class WorkspaceRole(StrEnum):
    owner = "owner"
    admin = "admin"
    member = "member"


class Workspace(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    slug: str = Field(unique=True, index=True, max_length=255)
    owner_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    owner: Optional["User"] = Relationship(back_populates="owned_workspaces")
    members: list["WorkspaceMember"] = Relationship(back_populates="workspace")
    boards: list["Board"] = Relationship(back_populates="workspace")


class WorkspaceMember(SQLModel, table=True):
    workspace_id: int = Field(foreign_key="workspace.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    role: WorkspaceRole = Field(default=WorkspaceRole.member)
    joined_at: datetime = Field(default_factory=datetime.utcnow)

    workspace: Optional[Workspace] = Relationship(back_populates="members")
    user: Optional["User"] = Relationship(back_populates="memberships")
