"""Settings. Everything environment-driven; no secrets in code."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Geek-Trainer API"
    environment: str = "development"
    debug: bool = True

    # Postgres. In development this is filled in by scripts/devdb.py, which
    # runs a real Postgres 16 from the pgserver wheel - no Docker, no sudo.
    # See PLAN.md D17.
    database_url: str = ""

    # Sec 24 - session cookie.
    session_cookie_name: str = "gt_session"
    session_ttl_days: int = 30
    cookie_secure: bool = False  # True everywhere but local http
    cookie_domain: str | None = None

    # Sec 24 - password reset.
    reset_token_ttl_minutes: int = 15

    # Sec 24 - login rate limiting.
    login_max_attempts_per_minute: int = 10

    # Origins allowed to make credentialed requests (CSRF defence, PLAN.md D9).
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
