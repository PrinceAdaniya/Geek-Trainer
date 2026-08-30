"""Authentication. SPECIFICATIONS.MD Sec 24, PLAN.md D9."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.clock import utcnow
from app.core.errors import NotAuthenticated, RateLimited, ValidationFailed
from app.core.security import (
    hash_password,
    hash_token,
    new_token,
    needs_rehash,
    password_problem,
    verify_password,
)
from app.domain.models import User
from app.mail.sender import get_sender
from app.repo import users as users_repo

# Sec 24 - identical responses whether or not the account exists, so neither
# registration nor password reset can be used to enumerate users.
_NEUTRAL_RESET_MESSAGE = (
    "If an account exists for that address, a reset link is on its way."
)


@dataclass
class LoginResult:
    user: User
    token: str


def register(
    db: Session, *, email: str, password: str, name: str, timezone_name: str
) -> User:
    problem = password_problem(password)
    if problem:
        raise ValidationFailed(problem, details={"field": "password"})

    existing = users_repo.get_by_email(db, email)
    if existing is not None:
        # Do not confirm the address is taken. The owner of the address gets
        # told by email; a stranger learns nothing.
        get_sender().send(
            to=existing.email,
            subject="Someone tried to register with your email",
            body=(
                "Somebody just tried to create a Geek-Trainer account with this "
                "address. If that was you, you already have one - try logging in, "
                "or reset your password. If it was not you, you can ignore this."
            ),
        )
        raise ValidationFailed(
            "Registration could not be completed. Check your email for details.",
            code="registration_unavailable",
        )

    return users_repo.create(
        db,
        email=email,
        password_hash=hash_password(password),
        name=name.strip(),
        timezone_name=timezone_name,
    )


def login(
    db: Session, *, email: str, password: str, ip: str, user_agent: str | None
) -> LoginResult:
    settings = get_settings()

    failures = users_repo.recent_failed_attempts(
        db, email=email, ip=ip, within_seconds=60
    )
    if failures >= settings.login_max_attempts_per_minute:
        raise RateLimited("Too many attempts. Wait a minute and try again.")

    user = users_repo.get_by_email(db, email)
    # Verify even when the user is missing, so a missing account and a wrong
    # password take the same time.
    stored_hash = user.password_hash if user else hash_password("not-a-real-password")
    ok = verify_password(stored_hash, password)

    if not user or not ok:
        users_repo.record_login_attempt(db, email=email, ip=ip, succeeded=False)
        raise NotAuthenticated("Email or password is incorrect.")

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    users_repo.record_login_attempt(db, email=email, ip=ip, succeeded=True)
    token = new_token()
    users_repo.create_auth_session(
        db,
        user_id=user.id,
        token_hash=hash_token(token),
        ttl_days=settings.session_ttl_days,
        user_agent=user_agent,
    )
    return LoginResult(user=user, token=token)


def logout(db: Session, token: str | None) -> None:
    if token:
        users_repo.revoke_auth_session(db, hash_token(token))


def logout_everywhere(db: Session, user: User) -> int:
    return users_repo.revoke_all_auth_sessions(db, user.id)


def user_for_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    row = users_repo.get_auth_session(db, hash_token(token))
    if row is None or row.revoked_at is not None or row.expires_at <= utcnow():
        return None
    user = users_repo.get_by_id(db, row.user_id)
    if user is None:
        return None
    users_repo.touch_auth_session(db, row, get_settings().session_ttl_days)
    return user


def request_password_reset(db: Session, *, email: str, reset_url_base: str) -> str:
    """Always returns the same neutral message (Sec 24)."""
    user = users_repo.get_by_email(db, email)
    if user is not None:
        token = new_token()
        users_repo.create_reset_token(
            db,
            user_id=user.id,
            token_hash=hash_token(token),
            ttl_minutes=get_settings().reset_token_ttl_minutes,
        )
        get_sender().send(
            to=user.email,
            subject="Reset your Geek-Trainer password",
            body=(
                f"Use this link within "
                f"{get_settings().reset_token_ttl_minutes} minutes:\n\n"
                f"{reset_url_base}?token={token}\n\n"
                "If you did not ask for this, nothing has changed and you can "
                "ignore this email."
            ),
        )
    return _NEUTRAL_RESET_MESSAGE


def confirm_password_reset(db: Session, *, token: str, password: str) -> None:
    problem = password_problem(password)
    if problem:
        raise ValidationFailed(problem, details={"field": "password"})

    row = users_repo.get_reset_token(db, hash_token(token))
    if row is None or row.used_at is not None or row.expires_at <= utcnow():
        raise ValidationFailed(
            "That reset link is no longer valid. Request a new one.",
            code="reset_token_invalid",
        )

    user = users_repo.get_by_id(db, row.user_id)
    if user is None:
        raise ValidationFailed("That reset link is no longer valid.",
                               code="reset_token_invalid")

    user.password_hash = hash_password(password)
    row.used_at = utcnow()
    # Sec 24 - a password change ends every existing session.
    users_repo.revoke_all_auth_sessions(db, user.id)
    db.flush()
