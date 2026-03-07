import logging
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from lanterna_magica.config import settings
from lanterna_magica.db import apply_migrations, create_pool
from lanterna_magica.resolvers import create_gql
from lanterna_magica.telemetry import (
    instrument_app,
    instrument_db,
    setup_telemetry,
    shutdown_telemetry,
)

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

WEB_PUBLIC = Path(__file__).parent.parent.parent / "web" / "resources" / "public"


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry()
    instrument_db()
    apply_migrations()
    pool = await create_pool()
    app.state.pool = pool
    app.state.graphql = create_gql(pool)
    logger.info("lanterna-magica started")
    yield
    await pool.close()
    shutdown_telemetry()
    logger.info("lanterna-magica stopped")


app = FastAPI(title="lanterna-magica", lifespan=lifespan)
instrument_app(app)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allow_origins,
    allow_credentials=settings.cors.allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    pool = app.state.pool
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return JSONResponse({"status": "ok"})
    except (asyncpg.PostgresError, OSError):
        logger.exception("Health check failed")
        return JSONResponse({"status": "degraded"}, status_code=503)


@app.api_route("/graphql", methods=["GET", "POST", "OPTIONS"])
async def graphql_endpoint(request: Request) -> Response:
    return await app.state.graphql.handle_request(request)


if (WEB_PUBLIC / "js").is_dir():
    app.mount("/js", StaticFiles(directory=WEB_PUBLIC / "js"), name="js")
if (WEB_PUBLIC / "css").is_dir():
    app.mount("/css", StaticFiles(directory=WEB_PUBLIC / "css"), name="css")


@app.get("/{path:path}")
async def spa_fallback(request: Request, path: str) -> Response:
    return FileResponse(WEB_PUBLIC / "index.html")
