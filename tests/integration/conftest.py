"""
Test fixtures for the lanterna-magica GraphQL API.

Prerequisites (in-process mode, the default):
  - PostgreSQL running on localhost:5433
  - A 'lanterna_magica_test' database owned by the 'lanterna_magica' user

External server mode (--server-url):
  - A running lanterna-magica instance at the given URL
  - PostgreSQL accessible via LANTERNA_DB__* env vars for test cleanup
"""

import os

# Must be set before importing app so Dynaconf loads the [testing] environment
os.environ["LANTERNA_ENV"] = "testing"

import httpx
import pytest
from httpx import ASGITransport

from lanterna_magica.data.utils import SENTINEL_UUID
from lanterna_magica.db import create_pool


def pytest_collection_modifyitems(items):
    for item in items:
        if "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


def pytest_addoption(parser):
    parser.addoption(
        "--server-url",
        default=None,
        help="Run integration tests against a live server instead of in-process ASGI",
    )


@pytest.fixture(scope="session")
def server_url(request):
    return request.config.getoption("--server-url")


@pytest.fixture(scope="session", autouse=True)
def _migrations(server_url):
    if server_url:
        return
    from lanterna_magica.db import apply_migrations

    apply_migrations()


@pytest.fixture(scope="session")
async def pool(_migrations):
    p = await create_pool()
    yield p
    await p.close()


@pytest.fixture
async def client(pool, server_url):
    if server_url:
        async with httpx.AsyncClient(base_url=server_url) as c:
            yield c
    else:
        from lanterna_magica.app import app
        from lanterna_magica.resolvers import create_gql

        app.state.pool = pool
        app.state.graphql = create_gql(pool)
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.fixture(autouse=True)
async def _clean_db(pool):
    """Truncate all tables after each test, then re-insert sentinel rows."""
    yield
    async with pool.acquire() as conn:
        await conn.execute(
            "TRUNCATE services, environments, configurations,"
            " shared_values, shared_value_revisions, config_substitutions"
            " CASCADE"
        )
        await conn.execute(
            "INSERT INTO services (id, name, description)"
            " VALUES ($1, '_global', 'Sentinel for unscoped configurations')",
            SENTINEL_UUID,
        )
        await conn.execute(
            "INSERT INTO environments (id, name, description)"
            " VALUES ($1, '_global', 'Sentinel for unscoped configurations')",
            SENTINEL_UUID,
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
