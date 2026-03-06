import logging
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
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
