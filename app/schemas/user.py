from datetime import datetime
from typing import Optional

from pydantic import EmailStr
from sqlmodel import SQLModel


class UserCreate(SQLModel):
    email: EmailStr
    password: str
    full_name: str


class UserRead(SQLModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime


class TokenPair(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(SQLModel):
    email: EmailStr
    password: str


class RefreshRequest(SQLModel):
    refresh_token: str


class LogoutRequest(SQLModel):
    refresh_token: Optional[str] = None
