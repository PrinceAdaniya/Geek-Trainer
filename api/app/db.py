"""Engine and session handling."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    pass


def normalize_url(url: str) -> str:
    """Pin the driver to psycopg 3. pgserver and most tooling hand out bare
    `postgresql://` URLs, which SQLAlchemy would resolve to psycopg2."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL is not set. Run `make devdb` (scripts/devdb.py) "
                "to start a local Postgres, or set it yourself."
            )
        _engine = create_engine(
            normalize_url(settings.database_url), pool_pre_ping=True, future=True
        )
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def reset_engine() -> None:
    """Tests point the app at a fresh database between runs."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    get_settings.cache_clear()


def session_factory() -> sessionmaker:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_db() -> Iterator[Session]:
    """FastAPI dependency. One transaction per request: commit on success,
    roll back on any exception."""
    db = session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
