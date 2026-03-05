from assertpy import assert_that
from conftest import gql

# -- Mutations --

CREATE_SERVICE = """
mutation CreateService($input: CreateServiceInput!) {
    createService(input: $input) {
        id name description createdAt updatedAt archivedAt
    }
}
"""

UPDATE_SERVICE = """
mutation UpdateService($input: UpdateServiceInput!) {
    updateService(input: $input) {
        id name description createdAt updatedAt archivedAt
    }
}
"""

ARCHIVE_SERVICE = """
mutation ArchiveService($id: ID!) {
    archiveService(id: $id) {
        id name archivedAt
    }
}
"""

UNARCHIVE_SERVICE = """
mutation UnarchiveService($id: ID!) {
    unarchiveService(id: $id) {
        id name archivedAt
    }
}
"""

# -- Queries --

SERVICES = """
query Services($includeArchived: Boolean, $first: Int, $after: String, $search: String) {
    services(includeArchived: $includeArchived, first: $first, after: $after, search: $search) {
        edges {
            node { id name description createdAt updatedAt archivedAt }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

SERVICE = """
query Service($id: ID!) {
    service(id: $id) {
        id name description createdAt updatedAt archivedAt
    }
}
"""


# -- Helpers --


async def _create_service(client, name="traefik", description=None):
    body = await gql(
        client, CREATE_SERVICE, {"input": {"name": name, "description": description}}
    )
    return body["data"]["createService"]


# -- Tests --


async def test_create_service(client):
    svc = await _create_service(client, "traefik", "reverse proxy")
    assert_that(svc["name"], "service name").is_equal_to("traefik")
    assert_that(svc["description"], "service description").is_equal_to("reverse proxy")
    assert_that(svc["id"], "service id").is_not_none()
    assert_that(svc["createdAt"], "createdAt timestamp").is_not_none()
    assert_that(svc["updatedAt"], "updatedAt timestamp").is_not_none()
    assert_that(svc["archivedAt"], "new service should not be archived").is_none()


async def test_create_service_minimal(client):
    svc = await _create_service(client, "nginx")
    assert_that(svc["name"], "service name").is_equal_to("nginx")
    assert_that(svc["description"], "description should be null when not provided").is_none()


async def test_create_service_duplicate_name(client):
    await _create_service(client, "traefik")
    body = await gql(
        client,
        CREATE_SERVICE,
        {"input": {"name": "traefik"}},
        expect_errors=True,
    )
    assert_that(body, "duplicate name should return errors").contains_key("errors")


async def test_service_by_id(client):
    svc = await _create_service(client)
    body = await gql(client, SERVICE, {"id": svc["id"]})
    found = body["data"]["service"]
    assert_that(found["id"], "fetched service id").is_equal_to(svc["id"])
    assert_that(found["name"], "fetched service name").is_equal_to(svc["name"])


async def test_service_by_id_not_found(client):
    body = await gql(client, SERVICE, {"id": "00000000-0000-0000-0000-ffffffffffff"})
    assert_that(body["data"]["service"], "non-existent id should return null").is_none()


async def test_services_list(client):
    await _create_service(client, "traefik")
    await _create_service(client, "nginx")

    body = await gql(client, SERVICES)
    edges = body["data"]["services"]["edges"]
    names = [e["node"]["name"] for e in edges]
    assert_that(names, "services list").contains("traefik", "nginx")


async def test_services_excludes_sentinel(client):
    body = await gql(client, SERVICES)
    edges = body["data"]["services"]["edges"]
    names = [e["node"]["name"] for e in edges]
    assert_that(names, "sentinel row should be hidden").does_not_contain("_global")


async def test_update_service(client):
    svc = await _create_service(client, "traefik")

    body = await gql(
        client,
        UPDATE_SERVICE,
        {"input": {"id": svc["id"], "description": "reverse proxy"}},
    )
    updated = body["data"]["updateService"]
    assert_that(updated["name"], "name unchanged").is_equal_to("traefik")
    assert_that(updated["description"], "description updated").is_equal_to("reverse proxy")
    assert_that(updated["updatedAt"], "updatedAt advanced").is_greater_than_or_equal_to(svc["updatedAt"])


async def test_update_service_partial(client):
    svc = await _create_service(client, "traefik", "original description")

    body = await gql(
        client,
        UPDATE_SERVICE,
        {"input": {"id": svc["id"], "name": "traefik-v2"}},
    )
    updated = body["data"]["updateService"]
    assert_that(updated["name"], "name updated").is_equal_to("traefik-v2")
    assert_that(updated["description"], "description preserved").is_equal_to("original description")


async def test_update_archived_service_fails(client):
    svc = await _create_service(client)
    await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})

    body = await gql(
        client,
        UPDATE_SERVICE,
        {"input": {"id": svc["id"], "name": "new-name"}},
        expect_errors=True,
    )
    assert_that(body, "updating archived service should return errors").contains_key("errors")


async def test_archive_service(client):
    svc = await _create_service(client)

    body = await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})
    archived = body["data"]["archiveService"]
    assert_that(archived["archivedAt"], "archivedAt should be set").is_not_none()


async def test_archive_hides_from_list(client):
    svc = await _create_service(client)
    await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})

    body = await gql(client, SERVICES)
    edges = body["data"]["services"]["edges"]
    ids = [e["node"]["id"] for e in edges]
    assert_that(ids, "archived service hidden from default list").does_not_contain(svc["id"])


async def test_include_archived(client):
    svc = await _create_service(client)
    await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})

    body = await gql(client, SERVICES, {"includeArchived": True})
    edges = body["data"]["services"]["edges"]
    ids = [e["node"]["id"] for e in edges]
    assert_that(ids, "archived service visible with includeArchived").contains(svc["id"])


async def test_unarchive_service(client):
    svc = await _create_service(client)
    await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})

    body = await gql(client, UNARCHIVE_SERVICE, {"id": svc["id"]})
    restored = body["data"]["unarchiveService"]
    assert_that(restored["archivedAt"], "archivedAt cleared after unarchive").is_none()

    body = await gql(client, SERVICES)
    ids = [e["node"]["id"] for e in body["data"]["services"]["edges"]]
    assert_that(ids, "unarchived service visible in default list").contains(svc["id"])


async def test_search_by_name(client):
    await _create_service(client, "traefik", "reverse proxy")
    await _create_service(client, "nginx", "web server")

    body = await gql(client, SERVICES, {"search": "traefik"})
    edges = body["data"]["services"]["edges"]
    assert_that(edges, "search by name result count").is_length(1)
    assert_that(edges[0]["node"]["name"], "matched service name").is_equal_to("traefik")


async def test_search_by_description(client):
    await _create_service(client, "traefik", "reverse proxy")
    await _create_service(client, "nginx", "web server")

    body = await gql(client, SERVICES, {"search": "web server"})
    edges = body["data"]["services"]["edges"]
    assert_that(edges, "search by description result count").is_length(1)
    assert_that(edges[0]["node"]["name"], "matched service name").is_equal_to("nginx")


async def test_search_case_insensitive(client):
    await _create_service(client, "Traefik")

    body = await gql(client, SERVICES, {"search": "traefik"})
    edges = body["data"]["services"]["edges"]
    assert_that(edges, "case-insensitive search result count").is_length(1)


async def test_pagination(client):
    for i in range(5):
        await _create_service(client, f"svc-{i:02d}")

    # First page
    body = await gql(client, SERVICES, {"first": 2})
    page1 = body["data"]["services"]
    assert_that(page1["edges"], "page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"], "page 1 has next page").is_true()

    # Second page
    body = await gql(client, SERVICES, {"first": 2, "after": page1["pageInfo"]["endCursor"]})
    page2 = body["data"]["services"]
    assert_that(page2["edges"], "page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"], "page 2 has next page").is_true()

    # Third page
    body = await gql(client, SERVICES, {"first": 2, "after": page2["pageInfo"]["endCursor"]})
    page3 = body["data"]["services"]
    assert_that(page3["edges"], "page 3 edge count").is_length(1)
    assert_that(page3["pageInfo"]["hasNextPage"], "page 3 has no next page").is_false()


async def test_pagination_with_search(client):
    for i in range(4):
        await _create_service(client, f"alpha-{i:02d}")
    await _create_service(client, "beta-00")

    body = await gql(client, SERVICES, {"search": "alpha", "first": 2})
    page1 = body["data"]["services"]
    assert_that(page1["edges"], "search page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"], "search page 1 has next page").is_true()

    body = await gql(
        client, SERVICES, {"search": "alpha", "first": 2, "after": page1["pageInfo"]["endCursor"]}
    )
    page2 = body["data"]["services"]
    assert_that(page2["edges"], "search page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"], "search page 2 has no next page").is_false()


async def test_cursor_invalid_with_changed_search(client):
    for i in range(3):
        await _create_service(client, f"svc-{i:02d}")

    body = await gql(client, SERVICES, {"search": "svc", "first": 1})
    cursor = body["data"]["services"]["pageInfo"]["endCursor"]

    # Use cursor from "svc" search with a different search string
    body = await gql(
        client,
        SERVICES,
        {"search": "other", "first": 1, "after": cursor},
        expect_errors=True,
    )
    assert_that(body, "mismatched search cursor should return errors").contains_key("errors")
