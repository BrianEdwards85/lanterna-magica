from assertpy import assert_that
from conftest import gql
from gql import (
    ARCHIVE_DIMENSION,
    CREATE_DIMENSION,
    DIMENSIONS,
    DIMENSIONS_BY_IDS,
    GET_DIMENSION_TYPES,
    UPDATE_DIMENSION,
    _get_type_id,
    create_dimension,
    create_dimension_type,
)
from utils import nodes

# -- Tests --


async def test_create_dimension(client):
    type_id = await _get_type_id(client, "service")
    dim = await create_dimension(client, type_id, "traefik", "reverse proxy")
    assert_that(dim["name"]).described_as("dimension name").is_equal_to("traefik")
    assert_that(dim["description"]).described_as("dimension description").is_equal_to("reverse proxy")
    assert_that(dim["base"]).described_as("not a base dimension").is_false()
    assert_that(dim["type"]["id"]).described_as("type reference").is_equal_to(type_id)
    assert_that(dim["id"]).described_as("dimension id").is_not_none()
    assert_that(dim["createdAt"]).described_as("createdAt timestamp").is_not_none()
    assert_that(dim["archivedAt"]).described_as("new dimension not archived").is_none()


async def test_create_dimension_minimal(client):
    type_id = await _get_type_id(client, "service")
    dim = await create_dimension(client, type_id, "nginx")
    assert_that(dim["name"]).described_as("dimension name").is_equal_to("nginx")
    assert_that(dim["description"]).described_as("description when not provided").is_none()


async def test_create_dimension_duplicate_name_same_type(client):
    type_id = await _get_type_id(client, "service")
    await create_dimension(client, type_id, "traefik")
    body = await gql(
        client,
        CREATE_DIMENSION,
        {"input": {"typeId": type_id, "name": "traefik"}},
        expect_errors=True,
    )
    assert_that(body).described_as("duplicate name within type rejected").contains_key("errors")


async def test_create_dimension_same_name_different_type(client):
    """Same name is allowed across different dimension types."""
    type_id = await _get_type_id(client, "service")
    env_type = await create_dimension_type(client, "region")

    await create_dimension(client, type_id, "shared-name")
    dim2 = await create_dimension(client, env_type["id"], "shared-name")
    assert_that(dim2["name"]).described_as("same name different type").is_equal_to("shared-name")


async def test_dimensions_by_ids(client):
    type_id = await _get_type_id(client, "service")
    dim1 = await create_dimension(client, type_id, "traefik")
    dim2 = await create_dimension(client, type_id, "nginx")

    body = await gql(client, DIMENSIONS_BY_IDS, {"ids": [dim1["id"], dim2["id"]]})
    found = body["data"]["dimensionsByIds"]
    assert_that(found).described_as("fetched dimensions count").is_length(2)
    ids = [d["id"] for d in found]
    assert_that(ids).described_as("fetched dimension ids").contains(dim1["id"], dim2["id"])


async def test_dimensions_by_ids_empty(client):
    body = await gql(client, DIMENSIONS_BY_IDS, {"ids": []})
    found = body["data"]["dimensionsByIds"]
    assert_that(found).described_as("empty ids returns empty list").is_empty()


async def test_dimensions_by_ids_unknown(client):
    body = await gql(client, DIMENSIONS_BY_IDS, {"ids": ["00000000-0000-0000-0000-ffffffffffff"]})
    found = body["data"]["dimensionsByIds"]
    assert_that(found).described_as("unknown id returns empty list").is_empty()


async def test_dimensions_list(client):
    type_id = await _get_type_id(client, "service")
    await create_dimension(client, type_id, "traefik")
    await create_dimension(client, type_id, "nginx")

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("dimensions list").extracting("name").contains("traefik", "nginx")


async def test_dimensions_includes_base_by_default(client):
    """Base dimensions should appear by default."""
    type_id = await _get_type_id(client, "service")
    await create_dimension(client, type_id, "traefik")

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("base dimension included").extracting("name").contains("global")


async def test_dimensions_excludes_base_when_false(client):
    """Base dimensions should not appear when includeBase is false."""
    type_id = await _get_type_id(client, "service")
    await create_dimension(client, type_id, "traefik")

    body = await gql(client, DIMENSIONS, {"typeId": type_id, "includeBase": False})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("base dimension excluded").extracting("name").does_not_contain("global")


async def test_base_dimension_fields(client):
    """The base dimension has correct field values."""
    type_id = await _get_type_id(client, "service")

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    base = next(d for d in items if d["base"])
    assert_that(base["name"]).described_as("base name").is_equal_to("global")
    assert_that(base["base"]).described_as("base flag").is_true()
    assert_that(base["type"]["id"]).described_as("base type").is_equal_to(type_id)
    assert_that(base["archivedAt"]).described_as("base not archived").is_none()


async def test_base_dimension_by_id(client):
    """The base dimension can be fetched by ID."""
    type_id = await _get_type_id(client, "service")

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    base = next(d for d in items if d["base"])

    body = await gql(client, DIMENSIONS_BY_IDS, {"ids": [base["id"]]})
    results = body["data"]["dimensionsByIds"]
    assert_that(results).described_as("result list").is_length(1)
    found = results[0]
    assert_that(found["id"]).described_as("fetched base id").is_equal_to(base["id"])
    assert_that(found["name"]).described_as("fetched base name").is_equal_to("global")
    assert_that(found["base"]).described_as("fetched base flag").is_true()


async def test_base_dimension_not_updatable(client):
    """Base dimensions cannot be updated."""
    type_id = await _get_type_id(client, "service")

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    base = next(d for d in items if d["base"])

    body = await gql(
        client,
        UPDATE_DIMENSION,
        {"input": {"id": base["id"], "name": "renamed"}},
        expect_errors=True,
    )
    assert_that(body).described_as("base dimension update rejected").contains_key("errors")


async def test_base_dimension_not_archivable(client):
    """Base dimensions cannot be archived."""
    type_id = await _get_type_id(client, "service")

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    base = next(d for d in items if d["base"])

    body = await gql(client, ARCHIVE_DIMENSION, {"id": base["id"]}, expect_errors=True)
    assert_that(body).described_as("base dimension archive rejected").contains_key("errors")


async def test_each_type_has_base_dimension(client):
    """Every seeded dimension type should have a base dimension."""
    types_body = await gql(client, GET_DIMENSION_TYPES)
    for dt in types_body["data"]["dimensionTypes"]:
        body = await gql(client, DIMENSIONS, {"typeId": dt["id"]})
        items = nodes(body["data"]["dimensions"]["edges"])
        base_dims = [d for d in items if d["base"]]
        assert_that(base_dims).described_as(f"base dimension for type {dt['name']}").is_length(1)


async def test_dimensions_filtered_by_type(client):
    """Dimensions from one type should not appear when querying another."""
    type_id = await _get_type_id(client, "service")
    other_type = await create_dimension_type(client, "region")

    await create_dimension(client, type_id, "traefik")
    await create_dimension(client, other_type["id"], "us-east-1")

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("only service dimensions").extracting("name").contains("traefik").does_not_contain(
        "us-east-1"
    )
