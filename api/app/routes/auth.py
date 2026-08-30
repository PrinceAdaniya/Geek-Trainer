"""Auth endpoints. SPECIFICATIONS.MD Sec 23, Sec 24."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import client_ip, current_user, session_token
from app.domain.models import User
from app.domain.schemas import (
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
)
from app.routes.profile import build_profile
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
        path="/",
    )


def _clear_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        domain=settings.cookie_domain,
        path="/",
    )


@router.post("/register", status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user = auth_service.register(
        db,
        email=payload.email,
        password=payload.password,
        name=payload.name,
        timezone_name=payload.timezone,
    )
    result = auth_service.login(
        db,
        email=payload.email,
        password=payload.password,
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    _set_cookie(response, result.token)
    return build_profile(db, user)


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    result = auth_service.login(
        db,
        email=payload.email,
        password=payload.password,
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    _set_cookie(response, result.token)
    return build_profile(db, result.user)


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    auth_service.logout(db, session_token(request))
    _clear_cookie(response)
    return MessageResponse(message="Logged out.")


@router.post("/logout-all", response_model=MessageResponse)
def logout_all(
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    count = auth_service.logout_everywhere(db, user)
    _clear_cookie(response)
    return MessageResponse(message=f"Logged out of {count} session(s).")


@router.get("/me")
def me(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return build_profile(db, user)


@router.post("/password/reset-request", response_model=MessageResponse)
def reset_request(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    message = auth_service.request_password_reset(
        db, email=payload.email, reset_url_base="http://localhost:3000/reset"
    )
    return MessageResponse(message=message)


@router.post("/password/reset", response_model=MessageResponse)
def reset_confirm(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    auth_service.confirm_password_reset(
        db, token=payload.token, password=payload.password
    )
    return MessageResponse(message="Password updated. Please log in.")
