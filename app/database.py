"""Serverless-compatible PostgreSQL access (asyncpg).

Works against Vercel Postgres and Neon pooled endpoints. On serverless runtimes
no local file storage is available between invocations, so all state lives in
Postgres and connections are drawn from a small per-instance pool.
"""

import asyncio
import logging

import asyncpg

from app.config import Settings

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS links (
    id           BIGSERIAL PRIMARY KEY,
    short_code   TEXT NOT NULL UNIQUE,
    original_url TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clicks (
    id         BIGSERIAL PRIMARY KEY,
    short_code TEXT NOT NULL REFERENCES links(short_code) ON DELETE CASCADE,
    clicked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    referrer   TEXT
);

CREATE INDEX IF NOT EXISTS idx_clicks_short_code_time
    ON clicks (short_code, clicked_at DESC);
CREATE INDEX IF NOT EXISTS idx_links_created_at
    ON links (created_at DESC);
"""


def _normalize_connection(url: str) -> tuple[str, bool]:
    """Extract TLS intent from the DSN.

    Returns ``(dsn_without_sslmode, use_ssl)``. Pooled provider URLs commonly
    carry ``?sslmode=require``; asyncpg gets the requirement explicitly via the
    ``ssl`` argument instead of an arbitrary query parameter.
    """
    use_ssl = False
    dsn = url

    if dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql://", 1)

    if "sslmode=require" in dsn or "sslmode=required" in dsn:
        use_ssl = True

    if "?" in dsn:
        base, _, query = dsn.partition("?")
        params = [
            part for part in query.split("&") if not part.startswith("sslmode=")
        ]
        dsn = base + ("?" + "&".join(params) if params else "")

    return dsn, use_ssl


async def create_pool(settings: Settings) -> asyncpg.Pool:
    """Create a connection pool with retries for serverless cold starts.

    Neon/Vercel compute that has scaled to zero needs a moment to wake up, so
    the first connect often fails; we retry with exponential backoff.
    """
    dsn, use_ssl = _normalize_connection(settings.database_url)
    last_error: Exception | None = None

    for attempt in range(1, settings.db_retry_attempts + 1):
        try:
            pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=settings.pool_min_size,
                max_size=settings.pool_max_size,
                ssl=use_ssl,
                timeout=settings.db_connect_timeout,
                command_timeout=30,
            )
            logger.info("Database pool ready (attempt %s).", attempt)
            return pool
        except (OSError, asyncpg.PostgresError, asyncio.TimeoutError) as exc:
            last_error = exc
            logger.warning(
                "Database connection attempt %s/%s failed: %s",
                attempt,
                settings.db_retry_attempts,
                exc,
            )
            if attempt < settings.db_retry_attempts:
                delay = settings.db_retry_backoff * (2 ** (attempt - 1))
                await asyncio.sleep(delay)

    raise RuntimeError(
        f"Could not connect to the database after "
        f"{settings.db_retry_attempts} attempts: {last_error}"
    )


async def init_schema(pool: asyncpg.Pool) -> None:
    """Create tables and indexes idempotently."""
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    logger.info("Database schema is ready.")


async def ping(pool: asyncpg.Pool) -> bool:
    """Return True if the database answers a trivial query."""
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except (OSError, asyncpg.PostgresError):
        return False
