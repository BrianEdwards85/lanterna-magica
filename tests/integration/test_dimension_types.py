from assertpy import assert_that
from conftest import gql
from utils import create_dimension_type

# -- Mutations --

CREATE_DIMENSION_TYPE = """
mutation CreateDimensionType($input: CreateDimensionTypeInput!) {
    createDimensionType(input: $input) {
        id name priority createdAt archivedAt
    }
}
"""

ARCHIVE_DIMENSION_TYPE = """
mutation ArchiveDimensionType($id: ID!) {
    archiveDimensionType(id: $id) {
        id name archivedAt
    }
}
"""

UNARCHIVE_DIMENSION_TYPE = """
mutation UnarchiveDimensionType($id: ID!) {
    unarchiveDimensionType(id: $id) {
        id name archivedAt
    }
}
"""

# -- Queries --

DIMENSION_TYPES = """
query DimensionTypes($includeArchived: Boolean) {
    dimensionTypes(includeArchived: $includeArchived) {
        id name priority createdAt archivedAt
    }
}
"""

DIMENSION_TYPES_WITH_DIMENSIONS = """
query DimensionTypes {
    dimensionTypes {
        id name
        dimensions { edges { node { id name } } }
    }
}
"""


# -- Tests --


async def test_seed_dimension_types_exist(client):
    """The seed data should include service and environment types."""
    body = await gql(client, DIMENSION_TYPES)
    types = body["data"]["dimensionTypes"]
    names = [t["name"] for t in types]
    assert_that(names).described_as("seed dimension types").contains("service", "environment")


async def test_seed_types_ordered_by_priority(client):
    body = await gql(client, DIMENSION_TYPES)
    types = body["data"]["dimensionTypes"]
    priorities = [t["priority"] for t in types]
    assert_that(priorities).described_as("types ordered by priority").is_equal_to(
        sorted(priorities)
    )


async def test_create_dimension_type(client):
    dt = await create_dimension_type(client, "region", 10)
    assert_that(dt["name"]).described_as("dimension type name").is_equal_to("region")
    assert_that(dt["priority"]).described_as("dimension type priority").is_equal_to(10)
    assert_that(dt["id"]).described_as("dimension type id").is_not_none()
    assert_that(dt["createdAt"]).described_as("createdAt timestamp").is_not_none()
    assert_that(dt["archivedAt"]).described_as("new type not archived").is_none()


async def test_create_dimension_type_duplicate_name(client):
    await create_dimension_type(client, "region", 10)
    body = await gql(
        client,
        CREATE_DIMENSION_TYPE,
        {"input": {"name": "region", "priority": 11}},
        expect_errors=True,
    )
    assert_that(body).described_as("duplicate name rejected").contains_key("errors")


async def test_create_dimension_type_duplicate_priority(client):
    await create_dimension_type(client, "region", 10)
    body = await gql(
        client,
        CREATE_DIMENSION_TYPE,
        {"input": {"name": "tenant", "priority": 10}},
        expect_errors=True,
    )
    assert_that(body).described_as("duplicate priority rejected").contains_key("errors")


async def test_archive_dimension_type(client):
    dt = await create_dimension_type(client, "region", 10)

    body = await gql(client, ARCHIVE_DIMENSION_TYPE, {"id": dt["id"]})
    archived = body["data"]["archiveDimensionType"]
    assert_that(archived["archivedAt"]).described_as("archivedAt should be set").is_not_none()


async def test_archive_hides_from_list(client):
    dt = await create_dimension_type(client, "region", 10)
    await gql(client, ARCHIVE_DIMENSION_TYPE, {"id": dt["id"]})

    body = await gql(client, DIMENSION_TYPES)
    names = [t["name"] for t in body["data"]["dimensionTypes"]]
    assert_that(names).described_as("archived type hidden").does_not_contain("region")


async def test_include_archived(client):
    dt = await create_dimension_type(client, "region", 10)
    await gql(client, ARCHIVE_DIMENSION_TYPE, {"id": dt["id"]})

    body = await gql(client, DIMENSION_TYPES, {"includeArchived": True})
    names = [t["name"] for t in body["data"]["dimensionTypes"]]
    assert_that(names).described_as("archived type visible with includeArchived").contains("region")


async def test_unarchive_dimension_type(client):
    dt = await create_dimension_type(client, "region", 10)
    await gql(client, ARCHIVE_DIMENSION_TYPE, {"id": dt["id"]})

    body = await gql(client, UNARCHIVE_DIMENSION_TYPE, {"id": dt["id"]})
    restored = body["data"]["unarchiveDimensionType"]
    assert_that(restored["archivedAt"]).described_as("archivedAt cleared").is_none()

    body = await gql(client, DIMENSION_TYPES)
    names = [t["name"] for t in body["data"]["dimensionTypes"]]
    assert_that(names).described_as("unarchived type visible").contains("region")


async def test_dimension_type_has_dimensions_field(client):
    """DimensionType.dimensions should return its child dimensions."""
    body = await gql(client, DIMENSION_TYPES_WITH_DIMENSIONS)
    types = body["data"]["dimensionTypes"]
    # Seed types exist but base dimensions are excluded from list queries
    for t in types:
        assert_that(t).described_as("type has dimensions field").contains_key("dimensions")
