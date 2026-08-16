"""Shared test fixtures.

Tests run against a real PostgreSQL (the same DATABASE_URL the app uses) and
reset the tables between sessions so every assertion reads genuine, current
rows rather than stale state.
"""

import asyncio

import pytest

from app.database import _normalize_connection, SCHEMA_SQL
from app.config import get_settings


@pytest.fixture(scope="session")
def settings():
    return get_settings()


def _reset_db(database_url: str) -> None:
    async def run() -> None:
        dsn, use_ssl = _normalize_connection(database_url)
        conn = await asyncio.wait_for(
            asyncpg_connect(dsn, use_ssl), timeout=15
        )
        try:
            await conn.execute(SCHEMA_SQL)
            await conn.execute("TRUNCATE clicks, links RESTART IDENTITY CASCADE")
        finally:
            await conn.close()

    asyncio.run(run())


def asyncpg_connect(dsn: str, use_ssl: bool):
    import asyncpg

    return asyncpg.connect(dsn=dsn, ssl=use_ssl, timeout=10)


@pytest.fixture(scope="session", autouse=True)
def _session_cleanup(settings):
    yield
    _reset_db(settings.database_url)


@pytest.fixture(autouse=True)
def _clean_database(settings):
    _reset_db(settings.database_url)
    yield


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
