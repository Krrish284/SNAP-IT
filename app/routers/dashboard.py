"""Dashboard endpoints for Snap."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.config import Settings, get_settings
from app.dependencies import ConnDep
from app.models import DashboardResponse, RecentClick, TopLink
from app.services import links as links_service
from app.utils import build_short_url

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    conn: ConnDep,
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request,
) -> DashboardResponse:
    """Return totals, top links, and recent clicks."""
    data = await links_service.get_dashboard(conn, settings.dashboard_top_limit)

    top_links = [
        TopLink(
            short_code=row["short_code"],
            short_url=build_short_url(settings, request, row["short_code"]),
            original_url=row["original_url"],
            created_at=row["created_at"],
            click_count=row["click_count"],
            last_clicked_at=row["last_clicked_at"],
        )
        for row in data["top_links"]
    ]

    recent_clicks = [
        RecentClick(
            short_code=row["short_code"],
            original_url=row["original_url"],
            clicked_at=row["clicked_at"],
            referrer=row["referrer"],
        )
        for row in data["recent_clicks"]
    ]

    return DashboardResponse(
        total_links=data["total_links"],
        total_clicks=data["total_clicks"],
        top_links=top_links,
        recent_clicks=recent_clicks,
    )
