"""Shared helpers used across routers."""

from fastapi import Request

from app.config import Settings

SHORT_CODE_PATTERN = r"^[a-zA-Z0-9]{2,12}$"

RESERVED_SHORT_CODES = {
    "api",
    "app",
    "dashboard",
    "docs",
    "favicon",
    "health",
    "index",
    "openapi",
    "redoc",
    "robots",
    "static",
    "styles",
}


def build_short_url(settings: Settings, request: Request, short_code: str) -> str:
    """Build the public URL for a short code.

    Uses ``BASE_URL`` when configured so links stay stable across preview
    deployments; otherwise derives the host from the incoming request.
    """
    base = settings.base_url.rstrip("/") if settings.base_url else str(request.base_url).rstrip("/")
    return f"{base}/{short_code}"
