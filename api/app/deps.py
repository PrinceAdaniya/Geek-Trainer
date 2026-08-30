"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import NotAuthenticated
from app.db import get_db
from app.domain.models import User
from app.services import auth as auth_service


def session_token(request: Request) -> str | None:
    return request.cookies.get(get_settings().session_cookie_name)


def current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    user = auth_service.user_for_token(db, session_token(request))
    if user is None:
        raise NotAuthenticated("Please log in.")
    return user


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
