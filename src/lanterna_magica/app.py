import logging
from contextlib import asynccontextmanager
from pathlib import Path

from ariadne import QueryType, load_schema_from_path, make_executable_schema
from ariadne.asgi import GraphQL
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from lanterna_magica.db import apply_migrations, create_pool

logger = logging.getLogger(__name__)

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"


class _GraphQLProxy:
    """Proxy that defers to the GraphQL ASGI app created during lifespan."""

    def __init__(self, app: FastAPI):
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        await self._app.state.graphql(scope, receive, send)


def _create_graphql(pool) -> GraphQL:
    type_defs = load_schema_from_path(str(SCHEMA_DIR))
    query = QueryType()

    @query.field("hello")
    async def resolve_hello(_obj, info):
        async with info.context["pool"].acquire() as conn:
            row = await conn.fetchval("SELECT 1")
        return f"lanterna-magica is alive (db={row})"

    schema = make_executable_schema(type_defs, query, convert_names_case=True)
    return GraphQL(
        schema,
        context_value=lambda request, _data=None: {"pool": pool},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    apply_migrations()
    pool = await create_pool()
    app.state.pool = pool
    app.state.graphql = _create_graphql(pool)
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
