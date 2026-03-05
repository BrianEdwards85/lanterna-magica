import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from lanterna_magica.db import apply_migrations, create_pool
from lanterna_magica.resolvers import create_gql

logger = logging.getLogger(__name__)


class _GraphQLProxy:
    """Proxy that defers to the GraphQL ASGI app created during lifespan."""

    def __init__(self, app: FastAPI):
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        await self._app.state.graphql(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    apply_migrations()
    pool = await create_pool()
    app.state.pool = pool
    app.state.graphql = create_gql(pool)
    logger.info("lanterna-magica started")
    yield
    await pool.close()
    logger.info("lanterna-magica stopped")


app = FastAPI(title="lanterna-magica", lifespan=lifespan)


@app.get("/health")
async def health():
    pool = app.state.pool
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return JSONResponse({"status": "ok"})
    except Exception:
        logger.exception("Health check failed")
        return JSONResponse({"status": "degraded"}, status_code=503)


app.mount("/graphql", _GraphQLProxy(app))
