"""Application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.errors import register_error_handlers
from app.repo import guard
from app.routes import (
    account,
    ai,
    auth,
    exercises,
    health,
    plans,
    profile,
    progress,
    sessions,
    stats,
    sync,
    tickets,
)

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()

    if settings.environment in ("development", "test"):
        # The scoping guard is a development and test instrument (see
        # app/repo/guard.py for why it is not on in production).
        guard.install()

    if settings.environment == "development":
        # The console email sender logs at INFO; without a handler Python drops
        # it, and password-reset links would be unreachable in development.
        mail_log = logging.getLogger("geektrainer.mail")
        if not mail_log.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("MAIL %(message)s"))
            mail_log.addHandler(handler)
        mail_log.setLevel(logging.INFO)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(profile.router, prefix=API_PREFIX)
    app.include_router(exercises.router, prefix=API_PREFIX)
    app.include_router(plans.router, prefix=API_PREFIX)
    app.include_router(sessions.router, prefix=API_PREFIX)
    app.include_router(stats.router, prefix=API_PREFIX)
    app.include_router(sync.router, prefix=API_PREFIX)
    app.include_router(progress.router, prefix=API_PREFIX)
    app.include_router(ai.router, prefix=API_PREFIX)
    app.include_router(account.router, prefix=API_PREFIX)
    app.include_router(tickets.router, prefix=API_PREFIX)

    return app


app = create_app()
