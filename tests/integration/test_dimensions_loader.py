from assertpy import assert_that
from conftest import gql
from gql import (
    ARCHIVE_DIMENSION,
    DIMENSION_TYPES_WITH_DIMENSIONS_FILTERED,
    DIMENSION_TYPES_WITH_DIMENSIONS_NESTED,
    _get_type_id,
    create_dimension,
    create_dimension_type,
)

# -- DataLoader tests --


async def test_dimension_types_with_dimensions_via_loader(client):
    """Querying dimensionTypes with nested dimensions uses the DataLoader (default params)."""
    type_id = await _get_type_id(client, "service")
    await create_dimension(client, type_id, "traefik")
    await create_dimension(client, type_id, "nginx")

    body = await gql(client, DIMENSION_TYPES_WITH_DIMENSIONS_NESTED)
    types = body["data"]["dimensionTypes"]
    assert_that(types).described_as("dimension types returned").is_not_empty()

    service_type = next(t for t in types if t["name"] == "service")
    dim_names = [e["node"]["name"] for e in service_type["dimensions"]["edges"]]
    assert_that(dim_names).described_as("service dimensions include traefik").contains("traefik")
    assert_that(dim_names).described_as("service dimensions include nginx").contains("nginx")
    assert_that(dim_names).described_as("service dimensions include base").contains("global")


async def test_dimension_types_loader_returns_correct_dimensions_per_type(client):
    """Each dimension type only sees its own dimensions via the DataLoader."""
    type_id = await _get_type_id(client, "service")
    region_type = await create_dimension_type(client, "region")

    await create_dimension(client, type_id, "traefik")
    await create_dimension(client, region_type["id"], "us-east-1")

    body = await gql(client, DIMENSION_TYPES_WITH_DIMENSIONS_NESTED)
    types = body["data"]["dimensionTypes"]

    service_type = next(t for t in types if t["name"] == "service")
    region_type_data = next(t for t in types if t["name"] == "region")

    service_names = [e["node"]["name"] for e in service_type["dimensions"]["edges"]]
    region_names = [e["node"]["name"] for e in region_type_data["dimensions"]["edges"]]

    assert_that(service_names).described_as("service dims").contains("traefik").does_not_contain("us-east-1")
    assert_that(region_names).described_as("region dims").contains("us-east-1").does_not_contain("traefik")


async def test_dimension_types_loader_excludes_archived(client):
    """DataLoader path excludes archived dimensions (default: include_archived=False)."""
    type_id = await _get_type_id(client, "service")
    dim = await create_dimension(client, type_id, "traefik")
    await gql(client, ARCHIVE_DIMENSION, {"id": dim["id"]})

    body = await gql(client, DIMENSION_TYPES_WITH_DIMENSIONS_NESTED)
    types = body["data"]["dimensionTypes"]
    service_type = next(t for t in types if t["name"] == "service")
    dim_names = [e["node"]["name"] for e in service_type["dimensions"]["edges"]]
    assert_that(dim_names).described_as("archived dim not visible via loader").does_not_contain("traefik")


async def test_dimension_types_loader_fallback_with_include_archived(client):
    """Passing includeArchived=True falls back to direct call, includes archived dims."""
    type_id = await _get_type_id(client, "service")
    dim = await create_dimension(client, type_id, "traefik")
    await gql(client, ARCHIVE_DIMENSION, {"id": dim["id"]})

    body = await gql(client, DIMENSION_TYPES_WITH_DIMENSIONS_FILTERED, {"includeArchived": True})
    types = body["data"]["dimensionTypes"]
    service_type = next(t for t in types if t["name"] == "service")
    dim_names = [e["node"]["name"] for e in service_type["dimensions"]["edges"]]
    assert_that(dim_names).described_as("archived dim visible with includeArchived=True").contains("traefik")


async def test_dimension_types_loader_fallback_with_search(client):
    """Passing search= falls back to direct call, filters dimensions by name."""
    type_id = await _get_type_id(client, "service")
    await create_dimension(client, type_id, "traefik")
    await create_dimension(client, type_id, "nginx")

    body = await gql(client, DIMENSION_TYPES_WITH_DIMENSIONS_FILTERED, {"search": "traefik"})
    types = body["data"]["dimensionTypes"]
    service_type = next(t for t in types if t["name"] == "service")
    dim_names = [e["node"]["name"] for e in service_type["dimensions"]["edges"]]
    assert_that(dim_names).described_as("search filters to traefik only").contains("traefik").does_not_contain("nginx")


async def test_dimension_types_loader_fallback_with_pagination(client):
    """Passing first= falls back to direct call and respects pagination."""
    type_id = await _get_type_id(client, "service")
    for i in range(3):
        await create_dimension(client, type_id, f"svc-{i:02d}")

    body = await gql(client, DIMENSION_TYPES_WITH_DIMENSIONS_FILTERED, {"first": 2})
    types = body["data"]["dimensionTypes"]
    service_type = next(t for t in types if t["name"] == "service")
    assert_that(service_type["dimensions"]["edges"]).described_as("paginated result").is_length(2)
    assert_that(service_type["dimensions"]["pageInfo"]["hasNextPage"]).described_as("has next page").is_true()
