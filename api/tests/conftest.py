"""Test harness.

Runs against a real PostgreSQL 16 provided by the pgserver wheel (PLAN.md D17)
- no Docker, no sudo, no system install. The schema is built by running the
actual migrations, so a migration that does not apply fails the suite.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pgserver
import pytest
from sqlalchemy import create_engine, text

API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))

TEST_PGDATA = API_DIR / ".pgdata-test"
TEST_DB = "geektrainer_test"


def _test_database_url() -> str:
    TEST_PGDATA.mkdir(parents=True, exist_ok=True)
    server = pgserver.get_server(str(TEST_PGDATA), cleanup_mode=None)
    admin_uri = server.get_uri()
    admin = create_engine(
        admin_uri.replace("postgresql://", "postgresql+psycopg://"),
        isolation_level="AUTOCOMMIT",
    )
    with admin.connect() as conn:
        exists = conn.execute(
            text("select 1 from pg_database where datname = :n"), {"n": TEST_DB}
        ).scalar()
        if not exists:
            conn.execute(text(f'create database "{TEST_DB}"'))
    admin.dispose()
    return server.get_uri(database=TEST_DB)


@pytest.fixture(scope="session", autouse=True)
def database() -> str:
    url = _test_database_url()
    os.environ["DATABASE_URL"] = url
    os.environ["ENVIRONMENT"] = "test"

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_DIR,
        check=True,
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
    )

    from app.config import get_settings
    from app.db import reset_engine
    from app.repo import guard

    reset_engine()
    get_settings.cache_clear()
    # Install the scoping guard for the whole suite, not just for tests that
    # happen to build an app first.
    guard.install()
    return url


@pytest.fixture(autouse=True)
def clean_tables(database):
    """Each test starts from an empty database."""
    from app.db import get_engine
    from app.repo.guard import unscoped

    engine = get_engine()
    with unscoped("test teardown truncates every table"):
        with engine.begin() as conn:
            tables = [
                r[0]
                for r in conn.execute(
                    text(
                        "select tablename from pg_tables where schemaname='public' "
                        "and tablename <> 'alembic_version'"
                    )
                )
            ]
            if tables:
                conn.execute(
                    text(
                        "truncate table "
                        + ", ".join(f'"{t}"' for t in tables)
                        + " restart identity cascade"
                    )
                )
    yield


@pytest.fixture
def app(database):
    from app.main import create_app

    return create_app()


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture
def db(database):
    from app.db import session_factory

    session = session_factory()()
    try:
        yield session
        session.commit()
    finally:
        session.close()


def register(client, *, email: str | None = None, password: str = "correct-horse-battery",
             name: str = "Test User", timezone: str = "UTC"):
    """Register a user and return (response, credentials)."""
    email = email or f"user-{uuid.uuid4().hex[:10]}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": name, "timezone": timezone},
    )
    return response, {"email": email, "password": password}


@pytest.fixture
def user_client(client):
    """A logged-in client."""
    response, creds = register(client)
    assert response.status_code == 201, response.text
    client.creds = creds
    client.profile = response.json()
    return client
