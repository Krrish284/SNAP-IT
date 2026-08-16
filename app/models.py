"""Pydantic schemas for the Snap API."""

import re
from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator

SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")


class ShortenRequest(BaseModel):
    """Request body for creating a short link."""

    url: str = Field(min_length=1, max_length=2048)

    @field_validator("url")
    @classmethod
    def normalize_and_validate_url(cls, value: str) -> str:
        """Trim, default the scheme, and reject unsafe/invalid URLs."""
        value = value.strip()
        if not value:
            raise ValueError("URL must not be empty")
        if any(char.isspace() for char in value):
            raise ValueError("URL must not contain whitespace")
        if not SCHEME_RE.match(value):
            value = f"https://{value}"

        try:
            parsed = urlsplit(value)
        except ValueError as exc:
            raise ValueError("URL is malformed") from exc

        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL scheme must be http or https")
        if not parsed.netloc:
            raise ValueError("URL must include a host")
        host = parsed.hostname or ""
        if "." not in host:
            raise ValueError("URL host must include a domain")

        return value


class LinkOut(BaseModel):
    """Public representation of a shortened link."""

    short_code: str
    short_url: str
    original_url: str
    created_at: datetime


class LinkStats(LinkOut):
    """Link representation including click analytics."""

    click_count: int
    last_clicked_at: datetime | None = None


class RecentClick(BaseModel):
    """A single recorded click, enriched with the target link."""

    short_code: str
    original_url: str
    clicked_at: datetime
    referrer: str | None = None


class TopLink(LinkStats):
    """A link on the dashboard, ranked by click count."""


class DashboardResponse(BaseModel):
    """Aggregated dashboard payload."""

    total_links: int
    total_clicks: int
    top_links: list[TopLink]
    recent_clicks: list[RecentClick]


class ClickDay(BaseModel):
    """Click count grouped by calendar day."""

    date: datetime
    count: int


class ClicksTimeline(BaseModel):
    """Click timeline for a single link."""

    short_code: str
    total: int
    daily: list[ClickDay]


class HealthResponse(BaseModel):
    """Health check payload."""

    status: str
    database: str
