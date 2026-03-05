"""
Test fixtures for the lanterna-magica GraphQL API.

Prerequisites:
  - PostgreSQL running on localhost:5433
  - A 'lanterna_magica_test' database owned by the 'lanterna_magica' user
"""

import os

os.environ["LANTERNA_ENV"] = "testing"

import httpx
import pytest
from httpx import ASGITransport

from lanterna_magica.app import app
from lanterna_magica.data.utils import SENTINEL_UUID
from lanterna_magica.db import apply_migrations, create_pool
from lanterna_magica.resolvers import create_gql

@pytest.fixture(scope="session", autouse=True)
def _migrations():
    apply_migrations()


@pytest.fixture(scope="session")
async def pool(_migrations):
    p = await create_pool()
    yield p
    await p.close()


@pytest.fixture
async def client(pool):
    app.state.pool = pool
    app.state.graphql = create_gql(pool)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
async def _clean_db(pool):
    """Truncate services table after each test, preserving the sentinel row."""
    yield
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM config_substitutions")
        await conn.execute("DELETE FROM configurations")
        await conn.execute("DELETE FROM shared_value_revisions")
        await conn.execute("DELETE FROM shared_values")
        await conn.execute(
            "DELETE FROM environments WHERE id != $1", SENTINEL_UUID
        )
        await conn.execute(
            "DELETE FROM services WHERE id != $1", SENTINEL_UUID
        )


async def gql(
    client: httpx.AsyncClient,
    query: str,
    variables: dict | None = None,
    *,
    expect_errors: bool = False,
):
    """Send a GraphQL request and return the parsed response body."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    resp = await client.post("/graphql", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    if not expect_errors:
        assert "errors" not in body, body.get("errors")

    return body
