import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core import security
from app.core.config import settings
from app.models.user import RefreshToken, User
from app.schemas.user import UserCreate


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def register_user(session: Session, data: UserCreate) -> User:
    try:
        existing = session.exec(select(User).where(User.email == data.email)).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )
        user = User(
            email=str(data.email),
            hashed_password=security.get_password_hash(data.password),
            full_name=data.full_name,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not register user"
        ) from None


def authenticate(session: Session, email: str, password: str) -> tuple[str, str]:
    try:
        user = session.exec(select(User).where(User.email == email)).first()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        if not security.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        access = security.create_access_token(str(user.id))
        refresh = security.create_refresh_token(str(user.id))
        session.add(
            RefreshToken(
                user_id=user.id,
                token_hash=_hash_token(refresh),
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )
        )
        session.commit()
        return access, refresh
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
        ) from None


def refresh_tokens(session: Session, refresh_token: str) -> tuple[str, str]:
    try:
        subject = security.decode_token(refresh_token, "refresh")
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
        stored = session.exec(
            select(RefreshToken).where(RefreshToken.token_hash == _hash_token(refresh_token))
        ).first()
        now = datetime.now(timezone.utc)
        if stored is None or stored.revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
        stored_exp = stored.expires_at
        if stored_exp.tzinfo is None:
            stored_exp = stored_exp.replace(tzinfo=timezone.utc)
        if stored_exp < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
            )
        stored.revoked = True
        access = security.create_access_token(subject)
        new_refresh = security.create_refresh_token(subject)
        session.add(
            RefreshToken(
                user_id=int(subject),
                token_hash=_hash_token(new_refresh),
                expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )
        )
        session.commit()
        return access, new_refresh
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Refresh failed"
        ) from None


def logout(session: Session, user_id: int, refresh_token: str | None) -> None:
    try:
        if refresh_token is None:
            session.exec(select(RefreshToken).where(RefreshToken.user_id == user_id))
            tokens = session.exec(
                select(RefreshToken).where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked == False,  # noqa: E712
                )
            ).all()
            for tok in tokens:
                tok.revoked = True
        else:
            stored = session.exec(
                select(RefreshToken).where(RefreshToken.token_hash == _hash_token(refresh_token))
            ).first()
            if stored is not None and stored.user_id == user_id:
                stored.revoked = True
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        ) from None
