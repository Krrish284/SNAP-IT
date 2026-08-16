"""Link creation, lookup, and per-link analytics endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from app.config import Settings, get_settings
from app.dependencies import ConnDep
from app.models import ClicksTimeline, LinkOut, LinkStats, ShortenRequest
from app.services import links as links_service
from app.utils import SHORT_CODE_PATTERN, build_short_url

router = APIRouter(prefix="/api/links", tags=["links"])


@router.post(
    "",
    response_model=LinkOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_short_link(
    payload: ShortenRequest,
    request: Request,
    conn: ConnDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> LinkOut:
    """Shorten a URL and return the generated short link."""
    row = await links_service.create_link(conn, payload.url, settings)
    return LinkOut(
        short_code=row["short_code"],
        short_url=build_short_url(settings, request, row["short_code"]),
        original_url=row["original_url"],
        created_at=row["created_at"],
    )


@router.get("/{code}", response_model=LinkStats)
async def get_link(
    conn: ConnDep,
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request,
    code: Annotated[str, Path(pattern=SHORT_CODE_PATTERN)],
) -> LinkStats:
    """Return a link with its click count and last click time."""
    row = await links_service.get_link_stats(conn, code)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found",
        )
    return LinkStats(
        short_code=row["short_code"],
        short_url=build_short_url(settings, request, row["short_code"]),
        original_url=row["original_url"],
        created_at=row["created_at"],
        click_count=row["click_count"],
        last_clicked_at=row["last_clicked_at"],
    )


@router.get("/{code}/clicks", response_model=ClicksTimeline)
async def get_link_clicks(
    conn: ConnDep,
    code: Annotated[str, Path(pattern=SHORT_CODE_PATTERN)],
) -> ClicksTimeline:
    """Return the daily click timeline for a single link."""
    link = await links_service.get_link(conn, code)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found",
        )
    data = await links_service.get_link_timeline(conn, code)
    return ClicksTimeline(**data)
