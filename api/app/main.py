"""Application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.errors import register_error_handlers
from app.repo import guard
from app.routes import (
    auth,
    exercises,
    health,
    plans,
    profile,
    sessions,
    stats,
    sync,
)

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()

    if settings.environment in ("development", "test"):
        # The scoping guard is a development and test instrument (see
        # app/repo/guard.py for why it is not on in production).
        guard.install()

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

    return app


app = create_app()
