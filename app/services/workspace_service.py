from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.workspace import MemberAdd, WorkspaceCreate


def _ensure_member(session: Session, workspace_id: int, user_id: int) -> WorkspaceMember | None:
    return session.exec(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id
        )
    ).first()


def require_membership(session: Session, workspace_id: int, user_id: int) -> WorkspaceMember:
    member = _ensure_member(session, workspace_id, user_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member")
    return member


def require_role(
    session: Session, workspace_id: int, user_id: int, allowed: list[WorkspaceRole]
) -> WorkspaceMember:
    member = require_membership(session, workspace_id, user_id)
    if member.role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return member


def create_workspace(session: Session, owner_id: int, data: WorkspaceCreate) -> Workspace:
    try:
        existing = session.exec(select(Workspace).where(Workspace.slug == data.slug)).first()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
        owner = session.get(User, owner_id)
        if owner is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found")
        ws = Workspace(name=data.name, slug=data.slug, owner_id=owner_id)
        session.add(ws)
        session.flush()
        session.add(
            WorkspaceMember(workspace_id=ws.id, user_id=owner_id, role=WorkspaceRole.owner)
        )
        session.commit()
        session.refresh(ws)
        return ws
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create workspace"
        )


def list_user_workspaces(session: Session, user_id: int) -> list[Workspace]:
    memberships = session.exec(
        select(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
    ).all()
    ids = [m.workspace_id for m in memberships]
    if not ids:
        return []
    return list(session.exec(select(Workspace).where(Workspace.id.in_(ids))).all())


def add_member(session: Session, workspace_id: int, data: MemberAdd) -> WorkspaceMember:
    try:
        ws = session.get(Workspace, workspace_id)
        if ws is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
        user = session.get(User, data.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if _ensure_member(session, workspace_id, data.user_id) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member")
        member = WorkspaceMember(
            workspace_id=workspace_id, user_id=data.user_id, role=data.role
        )
        session.add(member)
        session.commit()
        session.refresh(member)
        return member
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not add member"
        )
