from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserRead,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, session: Session = Depends(get_session)) -> User:
    return auth_service.register_user(session, data)


@router.post("/login", response_model=TokenPair)
def login(data: LoginRequest, session: Session = Depends(get_session)) -> TokenPair:
    access, refresh = auth_service.authenticate(session, str(data.email), data.password)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
def refresh(data: RefreshRequest, session: Session = Depends(get_session)) -> TokenPair:
    access, refresh = auth_service.refresh_tokens(session, data.refresh_token)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    data: LogoutRequest,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    auth_service.logout(session, current.id, data.refresh_token)
    return None


@router.get("/me", response_model=UserRead)
def me(current: User = Depends(get_current_user)) -> User:
    return current
