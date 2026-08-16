"""Redirect endpoint that also records click analytics."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from fastapi.responses import RedirectResponse

from app.config import Settings, get_settings
from app.dependencies import ConnDep
from app.services import links as links_service
from app.utils import RESERVED_SHORT_CODES, SHORT_CODE_PATTERN

router = APIRouter()


@router.get("/{code}", include_in_schema=False)
async def redirect_to_original(
    code: Annotated[str, Path(pattern=SHORT_CODE_PATTERN)],
    request: Request,
    conn: ConnDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    """Resolve a short code, record the click, and redirect to the target.

    The click is tracked before redirecting but analytics failures never block
    the redirect itself.
    """
    if code.lower() in RESERVED_SHORT_CODES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found",
        )

    link = await links_service.get_link(conn, code)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found",
        )

    referrer = request.headers.get("referer")
    if referrer:
        referrer = referrer[: settings.max_referrer_length]

    await links_service.record_click(conn, code, referrer)
    return RedirectResponse(link["original_url"], status_code=status.HTTP_302_FOUND)
