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
    assert svc["name"] == "traefik"
    assert svc["description"] == "reverse proxy"
    assert svc["id"] is not None
    assert svc["createdAt"] is not None
    assert svc["updatedAt"] is not None
    assert svc["archivedAt"] is None


async def test_create_service_minimal(client):
    svc = await _create_service(client, "nginx")
    assert svc["name"] == "nginx"
    assert svc["description"] is None


async def test_create_service_duplicate_name(client):
    await _create_service(client, "traefik")
    body = await gql(
        client,
        CREATE_SERVICE,
        {"input": {"name": "traefik"}},
        expect_errors=True,
    )
    assert "errors" in body


async def test_service_by_id(client):
    svc = await _create_service(client)
    body = await gql(client, SERVICE, {"id": svc["id"]})
    found = body["data"]["service"]
    assert found["id"] == svc["id"]
    assert found["name"] == svc["name"]


async def test_service_by_id_not_found(client):
    body = await gql(client, SERVICE, {"id": "00000000-0000-0000-0000-ffffffffffff"})
    assert body["data"]["service"] is None


async def test_services_list(client):
    await _create_service(client, "traefik")
    await _create_service(client, "nginx")

    body = await gql(client, SERVICES)
    edges = body["data"]["services"]["edges"]
    names = [e["node"]["name"] for e in edges]
    assert "traefik" in names
    assert "nginx" in names


async def test_services_excludes_sentinel(client):
    body = await gql(client, SERVICES)
    edges = body["data"]["services"]["edges"]
    names = [e["node"]["name"] for e in edges]
    assert "_global" not in names


async def test_update_service(client):
    svc = await _create_service(client, "traefik")

    body = await gql(
        client,
        UPDATE_SERVICE,
        {"input": {"id": svc["id"], "description": "reverse proxy"}},
    )
    updated = body["data"]["updateService"]
    assert updated["name"] == "traefik"
    assert updated["description"] == "reverse proxy"
    assert updated["updatedAt"] >= svc["updatedAt"]


async def test_update_service_partial(client):
    svc = await _create_service(client, "traefik", "original description")

    body = await gql(
        client,
        UPDATE_SERVICE,
        {"input": {"id": svc["id"], "name": "traefik-v2"}},
    )
    updated = body["data"]["updateService"]
    assert updated["name"] == "traefik-v2"
    assert updated["description"] == "original description"


async def test_update_archived_service_fails(client):
    svc = await _create_service(client)
    await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})

    body = await gql(
        client,
        UPDATE_SERVICE,
        {"input": {"id": svc["id"], "name": "new-name"}},
        expect_errors=True,
    )
    assert "errors" in body


async def test_archive_service(client):
    svc = await _create_service(client)

    body = await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})
    archived = body["data"]["archiveService"]
    assert archived["archivedAt"] is not None


async def test_archive_hides_from_list(client):
    svc = await _create_service(client)
    await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})

    body = await gql(client, SERVICES)
    edges = body["data"]["services"]["edges"]
    ids = [e["node"]["id"] for e in edges]
    assert svc["id"] not in ids


async def test_include_archived(client):
    svc = await _create_service(client)
    await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})

    body = await gql(client, SERVICES, {"includeArchived": True})
    edges = body["data"]["services"]["edges"]
    ids = [e["node"]["id"] for e in edges]
    assert svc["id"] in ids


async def test_unarchive_service(client):
    svc = await _create_service(client)
    await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})

    body = await gql(client, UNARCHIVE_SERVICE, {"id": svc["id"]})
    restored = body["data"]["unarchiveService"]
    assert restored["archivedAt"] is None

    body = await gql(client, SERVICES)
    ids = [e["node"]["id"] for e in body["data"]["services"]["edges"]]
    assert svc["id"] in ids


async def test_search_by_name(client):
    await _create_service(client, "traefik", "reverse proxy")
    await _create_service(client, "nginx", "web server")

    body = await gql(client, SERVICES, {"search": "traefik"})
    edges = body["data"]["services"]["edges"]
    assert len(edges) == 1
    assert edges[0]["node"]["name"] == "traefik"


async def test_search_by_description(client):
    await _create_service(client, "traefik", "reverse proxy")
    await _create_service(client, "nginx", "web server")

    body = await gql(client, SERVICES, {"search": "web server"})
    edges = body["data"]["services"]["edges"]
    assert len(edges) == 1
    assert edges[0]["node"]["name"] == "nginx"


async def test_search_case_insensitive(client):
    await _create_service(client, "Traefik")

    body = await gql(client, SERVICES, {"search": "traefik"})
    edges = body["data"]["services"]["edges"]
    assert len(edges) == 1


async def test_pagination(client):
    for i in range(5):
        await _create_service(client, f"svc-{i:02d}")

    # First page
    body = await gql(client, SERVICES, {"first": 2})
    page1 = body["data"]["services"]
    assert len(page1["edges"]) == 2
    assert page1["pageInfo"]["hasNextPage"] is True

    # Second page
    body = await gql(client, SERVICES, {"first": 2, "after": page1["pageInfo"]["endCursor"]})
    page2 = body["data"]["services"]
    assert len(page2["edges"]) == 2
    assert page2["pageInfo"]["hasNextPage"] is True

    # Third page
    body = await gql(client, SERVICES, {"first": 2, "after": page2["pageInfo"]["endCursor"]})
    page3 = body["data"]["services"]
    assert len(page3["edges"]) == 1
    assert page3["pageInfo"]["hasNextPage"] is False


async def test_pagination_with_search(client):
    for i in range(4):
        await _create_service(client, f"alpha-{i:02d}")
    await _create_service(client, "beta-00")

    body = await gql(client, SERVICES, {"search": "alpha", "first": 2})
    page1 = body["data"]["services"]
    assert len(page1["edges"]) == 2
    assert page1["pageInfo"]["hasNextPage"] is True

    body = await gql(
        client, SERVICES, {"search": "alpha", "first": 2, "after": page1["pageInfo"]["endCursor"]}
    )
    page2 = body["data"]["services"]
    assert len(page2["edges"]) == 2
    assert page2["pageInfo"]["hasNextPage"] is False


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
    assert "errors" in body
