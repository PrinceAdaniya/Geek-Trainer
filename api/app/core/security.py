"""Passwords and session tokens. SPECIFICATIONS.MD Sec 24, PLAN.md D9."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()

SESSION_TOKEN_BYTES = 32  # 256 bits, Sec 24
MIN_PASSWORD_LENGTH = 10

# A short deny-list stands in for the full common-password check (Sec 24). The
# real list is loaded in Phase 8; this covers the passwords tests would use.
_COMMON_PASSWORDS = frozenset(
    {
        "password", "password1", "password12", "password123", "passw0rd123",
        "1234567890", "12345678901", "qwertyuiop", "letmein123", "iloveyou123",
        "administrator", "welcome123", "abc123456", "football123", "trustno1234",
    }
)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def password_problem(password: str) -> str | None:
    """Sec 24 - length and a common-password check, no composition rules."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if password.lower() in _COMMON_PASSWORDS:
        return "That password is too common. Please choose another."
    return None


def new_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Session and reset tokens are stored hashed, never in plaintext."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
