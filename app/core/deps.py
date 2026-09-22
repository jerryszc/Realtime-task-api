from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core import security
from app.db.session import get_session
from app.models.user import User

bearer_scheme = HTTPBearer(
    auto_error=True,
    description="Paste access_token as Bearer token",
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    token = credentials.credentials
    subject = security.decode_token(token, "access")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    try:
        user_id = int(subject)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
        ) from None
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_workspace_admin(
    workspace_id: int,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    from app.models.workspace import WorkspaceMember, WorkspaceRole

    member = session.get(WorkspaceMember, (workspace_id, current.id))
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")
    if member.role not in (WorkspaceRole.owner, WorkspaceRole.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current


def require_workspace_member(
    workspace_id: int,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    from app.models.workspace import WorkspaceMember

    member = session.get(WorkspaceMember, (workspace_id, current.id))
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")
    return current
