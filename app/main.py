"""Snap — a URL shortener with click analytics.

FastAPI application served on Vercel serverless (Python runtime). The module
name ``main`` and the ``app`` instance are the standard Vercel FastAPI
entrypoint (``app/main.py:app``).
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import create_pool, init_schema, ping
from app.models import HealthResponse
from app.routers import dashboard as dashboard_router
from app.routers import links as links_router
from app.routers import redirect as redirect_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the database pool and prepare the schema at startup."""
    settings = get_settings()
    pool = await create_pool(settings)
    await init_schema(pool)
    app.state.pool = pool
    yield
    await pool.close()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Snap",
        description="Snap — a URL shortener with click analytics.",
        version="1.0.0",
        lifespan=lifespan,
    )

    origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    @app.get("/api/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        """Health check that also verifies database connectivity."""
        db_ok = await ping(app.state.pool)
        return HealthResponse(status="ok", database="ok" if db_ok else "unreachable")

    app.include_router(links_router.router)
    app.include_router(dashboard_router.router)

    @app.get("/", include_in_schema=False)
    async def home() -> FileResponse:
        return FileResponse(PUBLIC_DIR / "index.html")

    @app.get("/dashboard", include_in_schema=False)
    async def dashboard_page() -> FileResponse:
        return FileResponse(PUBLIC_DIR / "dashboard.html")

    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")

    # Registered last so only unmatched single-segment paths reach the
    # short-code redirect.
    app.include_router(redirect_router.router)

    return app


app = create_app()
