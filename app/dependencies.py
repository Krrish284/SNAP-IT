"""Shared FastAPI dependencies."""

from typing import Annotated, AsyncGenerator

import asyncpg
from fastapi import Depends, Request


async def get_conn(
    request: Request,
) -> AsyncGenerator[asyncpg.Connection, None]:
    """Yield a pooled connection, always returning it to the pool afterwards."""
    pool: asyncpg.Pool = request.app.state.pool
    conn = await pool.acquire()
    try:
        yield conn
    finally:
        await pool.release(conn)


ConnDep = Annotated[asyncpg.Connection, Depends(get_conn)]
