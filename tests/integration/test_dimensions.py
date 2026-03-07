from assertpy import assert_that
from conftest import gql
from utils import create_dimension, create_dimension_type, nodes, parse_dt

# -- Mutations --

CREATE_DIMENSION = """
mutation CreateDimension($input: CreateDimensionInput!) {
    createDimension(input: $input) {
        id type { id name } name description base createdAt updatedAt archivedAt
    }
}
"""

UPDATE_DIMENSION = """
mutation UpdateDimension($input: UpdateDimensionInput!) {
    updateDimension(input: $input) {
        id type { id name } name description base createdAt updatedAt archivedAt
    }
}
"""

ARCHIVE_DIMENSION = """
mutation ArchiveDimension($id: ID!) {
    archiveDimension(id: $id) {
        id name archivedAt
    }
}
"""

UNARCHIVE_DIMENSION = """
mutation UnarchiveDimension($id: ID!) {
    unarchiveDimension(id: $id) {
        id name archivedAt
    }
}
"""

# -- Queries --

DIMENSIONS = """
query Dimensions($typeId: ID!, $includeArchived: Boolean, $first: Int, $after: String, $search: String) {
    dimensions(typeId: $typeId, includeArchived: $includeArchived, first: $first, after: $after, search: $search) {
        edges {
            node { id type { id } name description base createdAt updatedAt archivedAt }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

DIMENSION = """
query Dimension($id: ID!) {
    dimension(id: $id) {
        id type { id name } name description base createdAt updatedAt archivedAt
    }
}
"""


# -- Helpers --


async def _get_service_type_id(client):
    body = await gql(client, "{ dimensionTypes { id name } }")
    for t in body["data"]["dimensionTypes"]:
        if t["name"] == "service":
            return t["id"]


# -- Tests --


async def test_create_dimension(client):
    type_id = await _get_service_type_id(client)
    dim = await create_dimension(client, type_id, "traefik", "reverse proxy")
    assert_that(dim["name"]).described_as("dimension name").is_equal_to("traefik")
    assert_that(dim["description"]).described_as("dimension description").is_equal_to("reverse proxy")
    assert_that(dim["base"]).described_as("not a base dimension").is_false()
    assert_that(dim["type"]["id"]).described_as("type reference").is_equal_to(type_id)
    assert_that(dim["id"]).described_as("dimension id").is_not_none()
    assert_that(dim["createdAt"]).described_as("createdAt timestamp").is_not_none()
    assert_that(dim["archivedAt"]).described_as("new dimension not archived").is_none()


async def test_create_dimension_minimal(client):
    type_id = await _get_service_type_id(client)
    dim = await create_dimension(client, type_id, "nginx")
    assert_that(dim["name"]).described_as("dimension name").is_equal_to("nginx")
    assert_that(dim["description"]).described_as("description when not provided").is_none()


async def test_create_dimension_duplicate_name_same_type(client):
    type_id = await _get_service_type_id(client)
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
    type_id = await _get_service_type_id(client)
    env_type = await create_dimension_type(client, "region", 10)

    await create_dimension(client, type_id, "shared-name")
    dim2 = await create_dimension(client, env_type["id"], "shared-name")
    assert_that(dim2["name"]).described_as("same name different type").is_equal_to("shared-name")


async def test_dimension_by_id(client):
    type_id = await _get_service_type_id(client)
    dim = await create_dimension(client, type_id, "traefik")

    body = await gql(client, DIMENSION, {"id": dim["id"]})
    found = body["data"]["dimension"]
    assert_that(found["id"]).described_as("fetched dimension id").is_equal_to(dim["id"])
    assert_that(found["name"]).described_as("fetched dimension name").is_equal_to("traefik")


async def test_dimension_by_id_not_found(client):
    body = await gql(client, DIMENSION, {"id": "00000000-0000-0000-0000-ffffffffffff"})
    assert_that(body["data"]["dimension"]).described_as("non-existent id").is_none()


async def test_dimensions_list(client):
    type_id = await _get_service_type_id(client)
    await create_dimension(client, type_id, "traefik")
    await create_dimension(client, type_id, "nginx")

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("dimensions list").extracting("name").contains("traefik", "nginx")


async def test_dimensions_excludes_base(client):
    """Base dimensions should not appear in list queries."""
    type_id = await _get_service_type_id(client)
    await create_dimension(client, type_id, "traefik")

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("base dimension excluded").extracting("name").does_not_contain("global")


async def test_dimensions_filtered_by_type(client):
    """Dimensions from one type should not appear when querying another."""
    type_id = await _get_service_type_id(client)
    other_type = await create_dimension_type(client, "region", 10)

    await create_dimension(client, type_id, "traefik")
    await create_dimension(client, other_type["id"], "us-east-1")

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("only service dimensions").extracting("name").contains(
        "traefik"
    ).does_not_contain("us-east-1")


async def test_update_dimension(client):
    type_id = await _get_service_type_id(client)
    dim = await create_dimension(client, type_id, "traefik")

    body = await gql(
        client,
        UPDATE_DIMENSION,
        {"input": {"id": dim["id"], "description": "reverse proxy"}},
    )
    updated = body["data"]["updateDimension"]
    assert_that(updated["name"]).described_as("name unchanged").is_equal_to("traefik")
    assert_that(updated["description"]).described_as("description updated").is_equal_to("reverse proxy")
    assert_that(parse_dt(updated["updatedAt"])).described_as("updatedAt advanced").is_after(
        parse_dt(dim["updatedAt"])
    )


async def test_update_dimension_partial(client):
    type_id = await _get_service_type_id(client)
    dim = await create_dimension(client, type_id, "traefik", "original description")

    body = await gql(
        client,
        UPDATE_DIMENSION,
        {"input": {"id": dim["id"], "name": "traefik-v2"}},
    )
    updated = body["data"]["updateDimension"]
    assert_that(updated["name"]).described_as("name updated").is_equal_to("traefik-v2")
    assert_that(updated["description"]).described_as("description preserved").is_equal_to("original description")


async def test_update_dimension_no_fields_fails(client):
    type_id = await _get_service_type_id(client)
    dim = await create_dimension(client, type_id, "traefik")
    body = await gql(
        client,
        UPDATE_DIMENSION,
        {"input": {"id": dim["id"]}},
        expect_errors=True,
    )
    assert_that(body).described_as("no-op update rejected").contains_key("errors")


async def test_update_archived_dimension_fails(client):
    type_id = await _get_service_type_id(client)
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
    type_id = await _get_service_type_id(client)
    dim = await create_dimension(client, type_id, "traefik")

    body = await gql(client, ARCHIVE_DIMENSION, {"id": dim["id"]})
    archived = body["data"]["archiveDimension"]
    assert_that(archived["archivedAt"]).described_as("archivedAt should be set").is_not_none()


async def test_archive_hides_from_list(client):
    type_id = await _get_service_type_id(client)
    dim = await create_dimension(client, type_id, "traefik")
    await gql(client, ARCHIVE_DIMENSION, {"id": dim["id"]})

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("archived dimension hidden").extracting("id").does_not_contain(dim["id"])


async def test_include_archived(client):
    type_id = await _get_service_type_id(client)
    dim = await create_dimension(client, type_id, "traefik")
    await gql(client, ARCHIVE_DIMENSION, {"id": dim["id"]})

    body = await gql(client, DIMENSIONS, {"typeId": type_id, "includeArchived": True})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("archived dimension visible").extracting("id").contains(dim["id"])


async def test_unarchive_dimension(client):
    type_id = await _get_service_type_id(client)
    dim = await create_dimension(client, type_id, "traefik")
    await gql(client, ARCHIVE_DIMENSION, {"id": dim["id"]})

    body = await gql(client, UNARCHIVE_DIMENSION, {"id": dim["id"]})
    restored = body["data"]["unarchiveDimension"]
    assert_that(restored["archivedAt"]).described_as("archivedAt cleared").is_none()

    body = await gql(client, DIMENSIONS, {"typeId": type_id})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("unarchived dimension visible").extracting("id").contains(dim["id"])


async def test_search_by_name(client):
    type_id = await _get_service_type_id(client)
    await create_dimension(client, type_id, "traefik", "reverse proxy")
    await create_dimension(client, type_id, "nginx", "web server")

    body = await gql(client, DIMENSIONS, {"typeId": type_id, "search": "traefik"})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("search by name").is_length(1)
    assert_that(items[0]["name"]).is_equal_to("traefik")


async def test_search_by_description(client):
    type_id = await _get_service_type_id(client)
    await create_dimension(client, type_id, "traefik", "reverse proxy")
    await create_dimension(client, type_id, "nginx", "web server")

    body = await gql(client, DIMENSIONS, {"typeId": type_id, "search": "web server"})
    items = nodes(body["data"]["dimensions"]["edges"])
    assert_that(items).described_as("search by description").is_length(1)
    assert_that(items[0]["name"]).is_equal_to("nginx")


async def test_pagination(client):
    type_id = await _get_service_type_id(client)
    for i in range(5):
        await create_dimension(client, type_id, f"dim-{i:02d}")

    body = await gql(client, DIMENSIONS, {"typeId": type_id, "first": 2})
    page1 = body["data"]["dimensions"]
    assert_that(page1["edges"]).described_as("page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as("page 1 has next page").is_true()

    body = await gql(client, DIMENSIONS, {"typeId": type_id, "first": 2, "after": page1["pageInfo"]["endCursor"]})
    page2 = body["data"]["dimensions"]
    assert_that(page2["edges"]).described_as("page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as("page 2 has next page").is_true()

    body = await gql(client, DIMENSIONS, {"typeId": type_id, "first": 2, "after": page2["pageInfo"]["endCursor"]})
    page3 = body["data"]["dimensions"]
    assert_that(page3["edges"]).described_as("page 3 edge count").is_length(1)
    assert_that(page3["pageInfo"]["hasNextPage"]).described_as("page 3 has no next page").is_false()
