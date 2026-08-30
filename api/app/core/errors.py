"""One error envelope for the whole API. SPECIFICATIONS.MD 23.1."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Raised anywhere in the app; rendered as the standard envelope."""

    status_code = 400
    code = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details or {}


class ValidationFailed(AppError):
    status_code = 422
    code = "validation_failed"


class NotAuthenticated(AppError):
    status_code = 401
    code = "not_authenticated"


class NotFound(AppError):
    """Also used for another user's resources - 23.1 forbids enumeration."""

    status_code = 404
    code = "not_found"


class Conflict(AppError):
    status_code = 409
    code = "conflict"


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"


def _envelope(code: str, message: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


def register_error_handlers(app) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_envelope(
                "validation_failed",
                "The request body failed validation.",
                {"fields": [
                    {"loc": [str(p) for p in e["loc"]], "msg": e["msg"]}
                    for e in exc.errors()
                ]},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {401: "not_authenticated", 403: "forbidden", 404: "not_found",
                 405: "method_not_allowed", 429: "rate_limited"}
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(
                codes.get(exc.status_code, "error"), str(exc.detail), {}
            ),
        )
