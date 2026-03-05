import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from lanterna_magica.db import apply_migrations, create_pool
from lanterna_magica.resolvers import create_gql

logger = logging.getLogger(__name__)


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


@app.api_route("/graphql", methods=["GET", "POST"])
async def graphql_endpoint(request: Request) -> Response:
    return await app.state.graphql.handle_request(request)
