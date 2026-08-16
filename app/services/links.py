"""Link creation, redirect tracking, and analytics queries."""

from typing import Any

import asyncpg

from app.codegen import generate_short_code
from app.config import Settings

CREATE_LINK_SQL = """
INSERT INTO links (short_code, original_url)
VALUES ($1, $2)
ON CONFLICT (short_code) DO NOTHING
RETURNING short_code, original_url, created_at
"""

GET_LINK_SQL = """
SELECT short_code, original_url, created_at
FROM links
WHERE short_code = $1
"""

GET_LINK_STATS_SQL = """
SELECT l.short_code,
       l.original_url,
       l.created_at,
       COUNT(c.id)::bigint   AS click_count,
       MAX(c.clicked_at)     AS last_clicked_at
FROM links l
LEFT JOIN clicks c ON c.short_code = l.short_code
WHERE l.short_code = $1
GROUP BY l.short_code, l.original_url, l.created_at
"""

INSERT_CLICK_SQL = """
INSERT INTO clicks (short_code, referrer)
VALUES ($1, $2)
"""

DASHBOARD_TOTALS_SQL = """
SELECT (SELECT COUNT(*) FROM links) AS total_links,
       (SELECT COUNT(*) FROM clicks) AS total_clicks
"""

TOP_LINKS_SQL = """
SELECT l.short_code,
       l.original_url,
       l.created_at,
       COUNT(c.id)::bigint   AS click_count,
       MAX(c.clicked_at)     AS last_clicked_at
FROM links l
LEFT JOIN clicks c ON c.short_code = l.short_code
GROUP BY l.short_code, l.original_url, l.created_at
ORDER BY click_count DESC, l.created_at DESC
LIMIT $1
"""

RECENT_CLICKS_SQL = """
SELECT c.short_code,
       c.clicked_at,
       c.referrer,
       l.original_url
FROM clicks c
JOIN links l ON l.short_code = c.short_code
ORDER BY c.clicked_at DESC
LIMIT $1
"""

TIMELINE_SQL = """
SELECT date_trunc('day', clicked_at) AS date,
       COUNT(*)::bigint              AS count
FROM clicks
WHERE short_code = $1
GROUP BY date_trunc('day', clicked_at)
ORDER BY date ASC
"""

TIMELINE_TOTAL_SQL = """
SELECT COUNT(*)::bigint
FROM clicks
WHERE short_code = $1
"""


async def create_link(
    conn: asyncpg.Connection,
    original_url: str,
    settings: Settings,
) -> dict[str, Any]:
    """Insert a new link with a collision-safe random short code."""
    for _ in range(settings.create_link_attempts):
        code = generate_short_code(settings.short_code_length)
        row = await conn.fetchrow(CREATE_LINK_SQL, code, original_url)
        if row is not None:
            return dict(row)
    raise RuntimeError("Could not allocate a unique short code")


async def get_link(
    conn: asyncpg.Connection, short_code: str
) -> dict[str, Any] | None:
    """Fetch a single link by short code, or None."""
    row = await conn.fetchrow(GET_LINK_SQL, short_code)
    return dict(row) if row else None


async def get_link_stats(
    conn: asyncpg.Connection, short_code: str
) -> dict[str, Any] | None:
    """Fetch a link together with its click count and last click time."""
    row = await conn.fetchrow(GET_LINK_STATS_SQL, short_code)
    return dict(row) if row else None


async def record_click(
    conn: asyncpg.Connection, short_code: str, referrer: str | None
) -> None:
    """Record a single click. Never raises so redirects are not blocked."""
    try:
        await conn.execute(INSERT_CLICK_SQL, short_code, referrer)
    except (OSError, asyncpg.PostgresError) as exc:
        logger = __import__("logging").getLogger(__name__)
        logger.warning("Failed to record click for %s: %s", short_code, exc)


async def get_dashboard(
    conn: asyncpg.Connection, top_limit: int
) -> dict[str, Any]:
    """Return totals, top links, and recent clicks for the dashboard."""
    totals = await conn.fetchrow(DASHBOARD_TOTALS_SQL)
    top = await conn.fetch(TOP_LINKS_SQL, top_limit)
    recent = await conn.fetch(RECENT_CLICKS_SQL, top_limit)
    return {
        "total_links": int(totals["total_links"]),
        "total_clicks": int(totals["total_clicks"]),
        "top_links": [dict(row) for row in top],
        "recent_clicks": [dict(row) for row in recent],
    }


async def get_link_timeline(
    conn: asyncpg.Connection, short_code: str
) -> dict[str, Any]:
    """Return daily click counts and the total for one link."""
    daily = await conn.fetch(TIMELINE_SQL, short_code)
    total = await conn.fetchval(TIMELINE_TOTAL_SQL, short_code)
    return {
        "short_code": short_code,
        "total": int(total),
        "daily": [dict(row) for row in daily],
    }
