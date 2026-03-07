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

UPDATE_DIMENSION_TYPE = """
mutation UpdateDimensionType($input: UpdateDimensionTypeInput!) {
    updateDimensionType(input: $input) {
        id name priority createdAt archivedAt
    }
}
"""

SWAP_DIMENSION_TYPE_PRIORITIES = """
mutation SwapDimensionTypePriorities($idA: ID!, $idB: ID!) {
    swapDimensionTypePriorities(idA: $idA, idB: $idB) {
        id name priority
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
    dt = await create_dimension_type(client, "region")
    assert_that(dt["name"]).described_as("dimension type name").is_equal_to("region")
    assert_that(dt["priority"]).described_as("auto-assigned priority").is_greater_than(0)
    assert_that(dt["id"]).described_as("dimension type id").is_not_none()
    assert_that(dt["createdAt"]).described_as("createdAt timestamp").is_not_none()
    assert_that(dt["archivedAt"]).described_as("new type not archived").is_none()


async def test_create_dimension_type_priority_is_max_plus_one(client):
    a = await create_dimension_type(client, "region")
    b = await create_dimension_type(client, "tenant")
    assert_that(b["priority"]).described_as("priority is exactly max + 1").is_equal_to(a["priority"] + 1)


async def test_create_dimension_type_duplicate_name(client):
    await create_dimension_type(client, "region")
    body = await gql(
        client,
        CREATE_DIMENSION_TYPE,
        {"input": {"name": "region"}},
        expect_errors=True,
    )
    assert_that(body).described_as("duplicate name rejected").contains_key("errors")


async def test_archive_dimension_type(client):
    dt = await create_dimension_type(client, "region")

    body = await gql(client, ARCHIVE_DIMENSION_TYPE, {"id": dt["id"]})
    archived = body["data"]["archiveDimensionType"]
    assert_that(archived["archivedAt"]).described_as("archivedAt should be set").is_not_none()


async def test_archive_hides_from_list(client):
    dt = await create_dimension_type(client, "region")
    await gql(client, ARCHIVE_DIMENSION_TYPE, {"id": dt["id"]})

    body = await gql(client, DIMENSION_TYPES)
    names = [t["name"] for t in body["data"]["dimensionTypes"]]
    assert_that(names).described_as("archived type hidden").does_not_contain("region")


async def test_include_archived(client):
    dt = await create_dimension_type(client, "region")
    await gql(client, ARCHIVE_DIMENSION_TYPE, {"id": dt["id"]})

    body = await gql(client, DIMENSION_TYPES, {"includeArchived": True})
    names = [t["name"] for t in body["data"]["dimensionTypes"]]
    assert_that(names).described_as("archived type visible with includeArchived").contains("region")


async def test_unarchive_dimension_type(client):
    dt = await create_dimension_type(client, "region")
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
    for t in types:
        assert_that(t).described_as("type has dimensions field").contains_key("dimensions")


async def test_create_dimension_type_creates_base_dimension(client):
    """Creating a dimension type should also create a base 'global' dimension."""
    dt = await create_dimension_type(client, "region")

    dims_query = """
    query Dimensions($typeId: ID!) {
        dimensions(typeId: $typeId) {
            edges { node { id name base } }
        }
    }
    """
    body = await gql(client, dims_query, {"typeId": dt["id"]})
    items = [e["node"] for e in body["data"]["dimensions"]["edges"]]
    base_dims = [d for d in items if d["base"]]
    assert_that(base_dims).described_as("new type has base dimension").is_length(1)
    assert_that(base_dims[0]["name"]).described_as("base dimension name").is_equal_to("global")


async def test_update_dimension_type_name(client):
    dt = await create_dimension_type(client, "region")
    body = await gql(client, UPDATE_DIMENSION_TYPE, {
        "input": {"id": dt["id"], "name": "zone"}
    })
    updated = body["data"]["updateDimensionType"]
    assert_that(updated["name"]).described_as("updated name").is_equal_to("zone")
    assert_that(updated["priority"]).described_as("priority unchanged").is_equal_to(dt["priority"])


async def test_update_dimension_type_not_found(client):
    body = await gql(
        client,
        UPDATE_DIMENSION_TYPE,
        {"input": {"id": "00000000-0000-0000-0000-000000000099", "name": "x"}},
        expect_errors=True,
    )
    assert_that(body).described_as("not found error").contains_key("errors")


async def test_update_archived_dimension_type_rejected(client):
    dt = await create_dimension_type(client, "region")
    await gql(client, ARCHIVE_DIMENSION_TYPE, {"id": dt["id"]})
    body = await gql(
        client,
        UPDATE_DIMENSION_TYPE,
        {"input": {"id": dt["id"], "name": "region"}},
        expect_errors=True,
    )
    assert_that(body).described_as("archived type cannot be updated").contains_key("errors")


async def test_swap_dimension_type_priorities(client):
    a = await create_dimension_type(client, "region")
    b = await create_dimension_type(client, "tenant")
    body = await gql(client, SWAP_DIMENSION_TYPE_PRIORITIES, {"idA": a["id"], "idB": b["id"]})
    swapped = body["data"]["swapDimensionTypePriorities"]
    by_id = {s["id"]: s for s in swapped}
    assert_that(by_id[a["id"]]["priority"]).described_as("a got b's priority").is_equal_to(b["priority"])
    assert_that(by_id[b["id"]]["priority"]).described_as("b got a's priority").is_equal_to(a["priority"])


async def test_swap_reorders_list(client):
    """After swapping, the list query should reflect the new order."""
    a = await create_dimension_type(client, "region")
    b = await create_dimension_type(client, "tenant")
    await gql(client, SWAP_DIMENSION_TYPE_PRIORITIES, {"idA": a["id"], "idB": b["id"]})
    body = await gql(client, DIMENSION_TYPES)
    names = [t["name"] for t in body["data"]["dimensionTypes"]]
    idx_a = names.index("region")
    idx_b = names.index("tenant")
    assert_that(idx_b).described_as("tenant now before region").is_less_than(idx_a)


async def test_swap_with_self_rejected(client):
    a = await create_dimension_type(client, "region")
    body = await gql(
        client,
        SWAP_DIMENSION_TYPE_PRIORITIES,
        {"idA": a["id"], "idB": a["id"]},
        expect_errors=True,
    )
    assert_that(body).described_as("swap with self rejected").contains_key("errors")


async def test_swap_with_nonexistent_id(client):
    a = await create_dimension_type(client, "region")
    body = await gql(
        client,
        SWAP_DIMENSION_TYPE_PRIORITIES,
        {"idA": a["id"], "idB": "00000000-0000-0000-0000-000000000099"},
        expect_errors=True,
    )
    assert_that(body).described_as("nonexistent id rejected").contains_key("errors")


async def test_swap_is_reversible(client):
    """Swapping twice should restore original priorities."""
    a = await create_dimension_type(client, "region")
    b = await create_dimension_type(client, "tenant")
    await gql(client, SWAP_DIMENSION_TYPE_PRIORITIES, {"idA": a["id"], "idB": b["id"]})
    await gql(client, SWAP_DIMENSION_TYPE_PRIORITIES, {"idA": a["id"], "idB": b["id"]})
    body = await gql(client, DIMENSION_TYPES)
    by_name = {t["name"]: t for t in body["data"]["dimensionTypes"]}
    assert_that(by_name["region"]["priority"]).described_as("region priority restored").is_equal_to(a["priority"])
    assert_that(by_name["tenant"]["priority"]).described_as("tenant priority restored").is_equal_to(b["priority"])
