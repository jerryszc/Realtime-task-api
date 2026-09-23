from typing import cast

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.deps import get_current_user, require_workspace_admin
from app.db.session import get_session
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.workspace import MemberAdd, MemberRead, WorkspaceCreate, WorkspaceRead
from app.services import workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(
    data: WorkspaceCreate,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Workspace:
    return workspace_service.create_workspace(session, cast(int, current.id), data)


@router.get("", response_model=list[WorkspaceRead])
def list_workspaces(
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[Workspace]:
    return workspace_service.list_user_workspaces(session, cast(int, current.id))


@router.post(
    "/{workspace_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    workspace_id: int,
    data: MemberAdd,
    current: User = Depends(require_workspace_admin),
    session: Session = Depends(get_session),
) -> WorkspaceMember:
    workspace_service.require_role(
        session, workspace_id, cast(int, current.id), [WorkspaceRole.owner, WorkspaceRole.admin]
    )
    return workspace_service.add_member(session, workspace_id, data)
