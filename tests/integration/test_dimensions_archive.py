import pytest
from assertpy import assert_that
from conftest import gql
from gql import (
    ARCHIVE_DIMENSION,
    DIMENSIONS,
    UNARCHIVE_DIMENSION,
    UPDATE_DIMENSION,
    _get_type_id,
    create_dimension,
)
from utils import nodes, parse_dt

from lanterna_magica.data.dimensions import Dimensions
from lanterna_magica.errors import NotFoundError


async def test_update_dimension(client):
    type_id = await _get_type_id(client, "service")
    dim = await create_dimension(client, type_id, "traefik")

    body = await gql(
        client,
        UPDATE_DIMENSION,
        {"input": {"id": dim["id"], "description": "reverse proxy"}},
    )
    updated = body["data"]["updateDimension"]
    assert_that(updated["name"]).described_as("name unchanged").is_equal_to("traefik")
    assert_that(updated["description"]).described_as("description updated").is_equal_to(
        "reverse proxy"
    )
    assert_that(parse_dt(updated["updatedAt"])).described_as(
        "updatedAt advanced"
    ).is_after(parse_dt(dim["updatedAt"]))


async def test_update_dimension_partial(client):
    type_id = await _get_type_id(client, "service")
    dim = await create_dimension(client, type_id, "traefik", "original description")

    body = await gql(
        client,
        UPDATE_DIMENSION,
        {"input": {"id": dim["id"], "name": "traefik-v2"}},
    )
    updated = body["data"]["updateDimension"]
    assert_that(updated["name"]).described_as("name updated").is_equal_to("traefik-v2")
    assert_that(updated["description"]).described_as(
        "description preserved"
    ).is_equal_to("original description")


async def test_update_dimension_no_fields_fails(client):
    type_id = await _get_type_id(client, "service")
    dim = await create_dimension(client, type_id, "traefik")
    body = await gql(
        client,
        UPDATE_DIMENSION,
        {"input": {"id": dim["id"]}},
        expect_errors=True,
    )
    assert_that(body).described_as("no-op update rejected").contains_key("errors")


async def test_update_archived_dimension_fails(client):
    type_id = await _get_type_id(client, "service")
    dim = await create_dimension(client, type_id, "traefik")
    await gql(client, ARCHIVE_DIMENSION, {"id": dim["id"]})

    body = await gql(
        client,
        UPDATE_DIMENSION,
        {"input": {"id": dim["id"], "name": "new-name"}},
        expect_errors=True,
    )
    assert_that(body).described_as("updating archived dimension").contains_key("errors")


async def test_archive_dimension(client):
    type_id = await _get_type_id(client, "service")
    dim = await create_dimension(client, type_id, "traefik")

    body = await gql(client, ARCHIVE_DIMENSION, {"id": dim["id"]})
    archived = body["data"]["archiveDimension"]
    assert_that(archived["archivedAt"]).described_as(
        "archivedAt should be set"
    ).is_not_none()


async def test_archive_hides_from_list(client):
    type_id = await _get_type_id(client, "service")
    dim = await create_dimension(client, type_id, "traefik")
    await gql(client, ARCHIVE_DIMENSION, {"id": dim["id"]})

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("archived dimension hidden").extracting(
        "id"
    ).does_not_contain(dim["id"])


async def test_include_archived(client):
    type_id = await _get_type_id(client, "service")
    dim = await create_dimension(client, type_id, "traefik")
    await gql(client, ARCHIVE_DIMENSION, {"id": dim["id"]})

    body = await gql(client, DIMENSIONS, {"typeId": type_id, "includeArchived": True})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("archived dimension visible").extracting(
        "id"
    ).contains(dim["id"])


async def test_unarchive_dimension(client):
    type_id = await _get_type_id(client, "service")
    dim = await create_dimension(client, type_id, "traefik")
    await gql(client, ARCHIVE_DIMENSION, {"id": dim["id"]})

    body = await gql(client, UNARCHIVE_DIMENSION, {"id": dim["id"]})
    restored = body["data"]["unarchiveDimension"]
    assert_that(restored["archivedAt"]).described_as("archivedAt cleared").is_none()

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("unarchived dimension visible").extracting(
        "id"
    ).contains(dim["id"])


async def test_search_by_name(client):
    type_id = await _get_type_id(client, "service")
    await create_dimension(client, type_id, "traefik", "reverse proxy")
    await create_dimension(client, type_id, "nginx", "web server")

    body = await gql(client, DIMENSIONS, {"typeId": type_id, "search": "traefik"})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("search by name").is_length(1)
    assert_that(items[0]["name"]).is_equal_to("traefik")


async def test_search_by_description(client):
    type_id = await _get_type_id(client, "service")
    await create_dimension(client, type_id, "traefik", "reverse proxy")
    await create_dimension(client, type_id, "nginx", "web server")

    body = await gql(client, DIMENSIONS, {"typeId": type_id, "search": "web server"})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("search by description").is_length(1)
    assert_that(items[0]["name"]).is_equal_to("nginx")


async def test_pagination(client):
    type_id = await _get_type_id(client, "service")
    for i in range(5):
        await create_dimension(client, type_id, f"dim-{i:02d}")

    body = await gql(client, DIMENSIONS, {"typeId": type_id, "first": 2})
    page1 = body["data"]["dimensions"]
    assert_that(page1["edges"]).described_as("page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as(
        "page 1 has next page"
    ).is_true()

    body = await gql(
        client,
        DIMENSIONS,
        {"typeId": type_id, "first": 2, "after": page1["pageInfo"]["endCursor"]},
    )
    page2 = body["data"]["dimensions"]
    assert_that(page2["edges"]).described_as("page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as(
        "page 2 has next page"
    ).is_true()

    body = await gql(
        client,
        DIMENSIONS,
        {"typeId": type_id, "first": 2, "after": page2["pageInfo"]["endCursor"]},
    )
    page3 = body["data"]["dimensions"]
    assert_that(page3["edges"]).described_as("page 3 edge count").is_length(2)
    assert_that(page3["pageInfo"]["hasNextPage"]).described_as(
        "page 3 has no next page"
    ).is_false()


# -- Data layer tests --


async def test_get_base_dimension(client, pool):
    """Dimensions.get_base_dimension returns the base dimension for a type."""
    type_id = await _get_type_id(client, "service")
    dims = Dimensions(pool)
    base = await dims.get_base_dimension(type_id)
    assert_that(base["name"]).described_as("base dimension name").is_equal_to("global")
    assert_that(base["base"]).described_as("base flag").is_true()
    assert_that(str(base["type_id"])).described_as("base type_id").is_equal_to(type_id)


async def test_get_base_dimension_not_found(pool):
    """get_base_dimension raises NotFoundError for a nonexistent type."""
    dims = Dimensions(pool)
    with pytest.raises(NotFoundError):
        await dims.get_base_dimension("00000000-0000-0000-0000-ffffffffffff")


async def test_get_by_ids_multi(client, pool):
    """Dimensions.get_by_ids returns multiple dimensions by ID."""
    type_id = await _get_type_id(client, "service")
    dim1 = await create_dimension(client, type_id, "traefik")
    dim2 = await create_dimension(client, type_id, "nginx")
    dims = Dimensions(pool)
    results = await dims.get_by_ids(ids=[dim1["id"], dim2["id"]])
    assert_that(results).described_as("multi-ID fetch count").is_length(2)
    result_ids = [str(r["id"]) for r in results]
    assert_that(result_ids).described_as("multi-ID fetch ids").contains(
        dim1["id"], dim2["id"]
    )


async def test_get_by_ids_empty(pool):
    """Dimensions.get_by_ids returns empty list for empty ids."""
    dims = Dimensions(pool)
    results = await dims.get_by_ids(ids=[])
    assert_that(results).described_as("empty ids returns empty list").is_empty()


async def test_get_by_ids_unknown(pool):
    """Dimensions.get_by_ids returns empty list for unknown IDs."""
    dims = Dimensions(pool)
    results = await dims.get_by_ids(ids=["00000000-0000-0000-0000-ffffffffffff"])
    assert_that(results).described_as("unknown id returns empty list").is_empty()
