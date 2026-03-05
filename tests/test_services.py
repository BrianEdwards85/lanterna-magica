from assertpy import assert_that
from conftest import gql
from utils import create_service, nodes, parse_dt

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


# -- Tests --


async def test_create_service(client):
    svc = await create_service(client, "traefik", "reverse proxy")
    assert_that(svc["name"]).described_as("service name").is_equal_to("traefik")
    assert_that(svc["description"]).described_as("service description").is_equal_to("reverse proxy")
    assert_that(svc["id"]).described_as("service id").is_not_none()
    assert_that(svc["createdAt"]).described_as("createdAt timestamp").is_not_none()
    assert_that(svc["updatedAt"]).described_as("updatedAt timestamp").is_not_none()
    assert_that(svc["archivedAt"]).described_as("new service should not be archived").is_none()


async def test_create_service_minimal(client):
    svc = await create_service(client, "nginx")
    assert_that(svc["name"]).described_as("service name").is_equal_to("nginx")
    assert_that(svc["description"]).described_as("description when not provided").is_none()


async def test_create_service_duplicate_name(client):
    await create_service(client, "traefik")
    body = await gql(
        client,
        CREATE_SERVICE,
        {"input": {"name": "traefik"}},
        expect_errors=True,
    )
    assert_that(body).described_as("duplicate name should return errors").contains_key("errors")


async def test_service_by_id(client):
    svc = await create_service(client)
    body = await gql(client, SERVICE, {"id": svc["id"]})
    found = body["data"]["service"]
    assert_that(found["id"]).described_as("fetched service id").is_equal_to(svc["id"])
    assert_that(found["name"]).described_as("fetched service name").is_equal_to(svc["name"])


async def test_service_by_id_not_found(client):
    body = await gql(client, SERVICE, {"id": "00000000-0000-0000-0000-ffffffffffff"})
    assert_that(body["data"]["service"]).described_as("non-existent id").is_none()


async def test_services_list(client):
    await create_service(client, "traefik")
    await create_service(client, "nginx")

    body = await gql(client, SERVICES)
    assert_that(nodes(body["data"]["services"]["edges"])).described_as(
        "services list"
    ).extracting("name").contains("traefik", "nginx")


async def test_services_excludes_sentinel(client):
    body = await gql(client, SERVICES)
    assert_that(nodes(body["data"]["services"]["edges"])).described_as(
        "sentinel row should be hidden"
    ).extracting("name").does_not_contain("_global")


async def test_update_service(client):
    svc = await create_service(client, "traefik")

    body = await gql(
        client,
        UPDATE_SERVICE,
        {"input": {"id": svc["id"], "description": "reverse proxy"}},
    )
    updated = body["data"]["updateService"]
    assert_that(updated["name"]).described_as("name unchanged").is_equal_to("traefik")
    assert_that(updated["description"]).described_as("description updated").is_equal_to(
        "reverse proxy"
    )
    assert_that(parse_dt(updated["updatedAt"])).described_as("updatedAt advanced").is_after(
        parse_dt(svc["updatedAt"])
    )


async def test_update_service_partial(client):
    svc = await create_service(client, "traefik", "original description")

    body = await gql(
        client,
        UPDATE_SERVICE,
        {"input": {"id": svc["id"], "name": "traefik-v2"}},
    )
    updated = body["data"]["updateService"]
    assert_that(updated["name"]).described_as("name updated").is_equal_to("traefik-v2")
    assert_that(updated["description"]).described_as("description preserved").is_equal_to(
        "original description"
    )


async def test_update_service_no_fields_fails(client):
    svc = await create_service(client)
    body = await gql(
        client,
        UPDATE_SERVICE,
        {"input": {"id": svc["id"]}},
        expect_errors=True,
    )
    assert_that(body).described_as("no-op update rejected").contains_key("errors")


async def test_update_archived_service_fails(client):
    svc = await create_service(client)
    await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})

    body = await gql(
        client,
        UPDATE_SERVICE,
        {"input": {"id": svc["id"], "name": "new-name"}},
        expect_errors=True,
    )
    assert_that(body).described_as("updating archived service").contains_key("errors")


async def test_archive_service(client):
    svc = await create_service(client)

    body = await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})
    archived = body["data"]["archiveService"]
    assert_that(archived["archivedAt"]).described_as("archivedAt should be set").is_not_none()


async def test_archive_hides_from_list(client):
    svc = await create_service(client)
    await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})

    body = await gql(client, SERVICES)
    assert_that(nodes(body["data"]["services"]["edges"])).described_as(
        "archived service hidden from default list"
    ).extracting("id").does_not_contain(svc["id"])


async def test_include_archived(client):
    svc = await create_service(client)
    await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})

    body = await gql(client, SERVICES, {"includeArchived": True})
    assert_that(nodes(body["data"]["services"]["edges"])).described_as(
        "archived service visible with includeArchived"
    ).extracting("id").contains(svc["id"])


async def test_unarchive_service(client):
    svc = await create_service(client)
    await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})

    body = await gql(client, UNARCHIVE_SERVICE, {"id": svc["id"]})
    restored = body["data"]["unarchiveService"]
    assert_that(restored["archivedAt"]).described_as(
        "archivedAt cleared after unarchive"
    ).is_none()

    body = await gql(client, SERVICES)
    assert_that(nodes(body["data"]["services"]["edges"])).described_as(
        "unarchived service visible in default list"
    ).extracting("id").contains(svc["id"])


async def test_search_by_name(client):
    await create_service(client, "traefik", "reverse proxy")
    await create_service(client, "nginx", "web server")

    body = await gql(client, SERVICES, {"search": "traefik"})
    edges = body["data"]["services"]["edges"]
    assert_that(edges).described_as("search by name result count").is_length(1)
    assert_that(edges[0]["node"]["name"]).described_as("matched service name").is_equal_to(
        "traefik"
    )


async def test_search_by_description(client):
    await create_service(client, "traefik", "reverse proxy")
    await create_service(client, "nginx", "web server")

    body = await gql(client, SERVICES, {"search": "web server"})
    edges = body["data"]["services"]["edges"]
    assert_that(edges).described_as("search by description result count").is_length(1)
    assert_that(edges[0]["node"]["name"]).described_as("matched service name").is_equal_to("nginx")


async def test_search_case_insensitive(client):
    await create_service(client, "Traefik")

    body = await gql(client, SERVICES, {"search": "traefik"})
    edges = body["data"]["services"]["edges"]
    assert_that(edges).described_as("case-insensitive search result count").is_length(1)


async def test_pagination(client):
    for i in range(5):
        await create_service(client, f"svc-{i:02d}")

    # First page
    body = await gql(client, SERVICES, {"first": 2})
    page1 = body["data"]["services"]
    assert_that(page1["edges"]).described_as("page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as("page 1 has next page").is_true()

    # Second page
    body = await gql(client, SERVICES, {"first": 2, "after": page1["pageInfo"]["endCursor"]})
    page2 = body["data"]["services"]
    assert_that(page2["edges"]).described_as("page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as("page 2 has next page").is_true()

    # Third page
    body = await gql(client, SERVICES, {"first": 2, "after": page2["pageInfo"]["endCursor"]})
    page3 = body["data"]["services"]
    assert_that(page3["edges"]).described_as("page 3 edge count").is_length(1)
    assert_that(page3["pageInfo"]["hasNextPage"]).described_as(
        "page 3 has no next page"
    ).is_false()


async def test_pagination_with_search(client):
    for i in range(4):
        await create_service(client, f"alpha-{i:02d}")
    await create_service(client, "beta-00")

    body = await gql(client, SERVICES, {"search": "alpha", "first": 2})
    page1 = body["data"]["services"]
    assert_that(page1["edges"]).described_as("search page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as(
        "search page 1 has next page"
    ).is_true()

    body = await gql(
        client, SERVICES, {"search": "alpha", "first": 2, "after": page1["pageInfo"]["endCursor"]}
    )
    page2 = body["data"]["services"]
    assert_that(page2["edges"]).described_as("search page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as(
        "search page 2 has no next page"
    ).is_false()


async def test_cursor_invalid_with_changed_search(client):
    for i in range(3):
        await create_service(client, f"svc-{i:02d}")

    body = await gql(client, SERVICES, {"search": "svc", "first": 1})
    cursor = body["data"]["services"]["pageInfo"]["endCursor"]

    # Use cursor from "svc" search with a different search string
    body = await gql(
        client,
        SERVICES,
        {"search": "other", "first": 1, "after": cursor},
        expect_errors=True,
    )
    assert_that(body).described_as("mismatched search cursor").contains_key("errors")


async def test_create_service_with_percent_in_name_fails(client):
    body = await gql(
        client, CREATE_SERVICE, {"input": {"name": "bad%name"}}, expect_errors=True
    )
    assert_that(body).described_as("percent in name rejected").contains_key("errors")


async def test_create_service_with_backslash_in_name_fails(client):
    body = await gql(
        client, CREATE_SERVICE, {"input": {"name": "bad\\name"}}, expect_errors=True
    )
    assert_that(body).described_as("backslash in name rejected").contains_key("errors")


async def test_update_service_with_percent_in_name_fails(client):
    svc = await create_service(client)
    body = await gql(
        client,
        UPDATE_SERVICE,
        {"input": {"id": svc["id"], "name": "bad%name"}},
        expect_errors=True,
    )
    assert_that(body).described_as("percent in update name rejected").contains_key("errors")


async def test_service_name_with_underscore_allowed(client):
    svc = await create_service(client, "my_service")
    assert_that(svc["name"]).described_as("underscore in name").is_equal_to("my_service")


async def test_search_underscore_literal(client):
    await create_service(client, "my_service")
    await create_service(client, "myXservice")

    body = await gql(client, SERVICES, {"search": "_"})
    edges = body["data"]["services"]["edges"]
    assert_that(edges).described_as("underscore search matches only literal _").is_length(1)
    assert_that(edges[0]["node"]["name"]).is_equal_to("my_service")


async def test_pagination_with_underscore_search(client):
    for i in range(3):
        await create_service(client, f"my_svc_{i:02d}")
    await create_service(client, "no-match")

    body = await gql(client, SERVICES, {"search": "_svc_", "first": 2})
    page1 = body["data"]["services"]
    assert_that(page1["edges"]).described_as("underscore search page 1").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).is_true()

    body = await gql(
        client, SERVICES, {"search": "_svc_", "first": 2, "after": page1["pageInfo"]["endCursor"]}
    )
    page2 = body["data"]["services"]
    assert_that(page2["edges"]).described_as("underscore search page 2").is_length(1)


async def test_search_strips_invalid_chars(client):
    await create_service(client, "traefik")

    body = await gql(client, SERVICES, {"search": "%traefik"})
    edges = body["data"]["services"]["edges"]
    assert_that(edges).described_as("search with stripped % still finds result").is_length(1)
    assert_that(edges[0]["node"]["name"]).is_equal_to("traefik")


# -- Error extension tests --


async def test_validation_error_has_extension_code(client):
    svc = await create_service(client)
    body = await gql(
        client,
        UPDATE_SERVICE,
        {"input": {"id": svc["id"]}},
        expect_errors=True,
    )
    error = body["errors"][0]
    assert_that(error["extensions"]["code"]).described_as(
        "validation error code"
    ).is_equal_to("VALIDATION_ERROR")


async def test_not_found_error_has_extension_code(client):
    svc = await create_service(client)
    await gql(client, ARCHIVE_SERVICE, {"id": svc["id"]})

    body = await gql(
        client,
        UPDATE_SERVICE,
        {"input": {"id": svc["id"], "name": "new-name"}},
        expect_errors=True,
    )
    error = body["errors"][0]
    assert_that(error["extensions"]["code"]).described_as(
        "not found error code"
    ).is_equal_to("NOT_FOUND")
