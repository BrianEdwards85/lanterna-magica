from assertpy import assert_that
from conftest import gql

# -- Mutations --

CREATE_ENVIRONMENT = """
mutation CreateEnvironment($input: CreateEnvironmentInput!) {
    createEnvironment(input: $input) {
        id name description createdAt updatedAt archivedAt
    }
}
"""

UPDATE_ENVIRONMENT = """
mutation UpdateEnvironment($input: UpdateEnvironmentInput!) {
    updateEnvironment(input: $input) {
        id name description createdAt updatedAt archivedAt
    }
}
"""

ARCHIVE_ENVIRONMENT = """
mutation ArchiveEnvironment($id: ID!) {
    archiveEnvironment(id: $id) {
        id name archivedAt
    }
}
"""

UNARCHIVE_ENVIRONMENT = """
mutation UnarchiveEnvironment($id: ID!) {
    unarchiveEnvironment(id: $id) {
        id name archivedAt
    }
}
"""

# -- Queries --

ENVIRONMENTS = """
query Environments($includeArchived: Boolean, $first: Int, $after: String, $search: String) {
    environments(includeArchived: $includeArchived, first: $first, after: $after, search: $search) {
        edges {
            node { id name description createdAt updatedAt archivedAt }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

ENVIRONMENT = """
query Environment($id: ID!) {
    environment(id: $id) {
        id name description createdAt updatedAt archivedAt
    }
}
"""


# -- Helpers --


async def _create_environment(client, name="production", description=None):
    body = await gql(
        client, CREATE_ENVIRONMENT, {"input": {"name": name, "description": description}}
    )
    return body["data"]["createEnvironment"]


# -- Tests --


async def test_create_environment(client):
    env = await _create_environment(client, "production", "prod cluster")
    assert_that(env["name"], "environment name").is_equal_to("production")
    assert_that(env["description"], "environment description").is_equal_to("prod cluster")
    assert_that(env["id"], "environment id").is_not_none()
    assert_that(env["createdAt"], "createdAt timestamp").is_not_none()
    assert_that(env["updatedAt"], "updatedAt timestamp").is_not_none()
    assert_that(env["archivedAt"], "new environment should not be archived").is_none()


async def test_create_environment_minimal(client):
    env = await _create_environment(client, "staging")
    assert_that(env["name"], "environment name").is_equal_to("staging")
    assert_that(env["description"], "description should be null when not provided").is_none()


async def test_create_environment_duplicate_name(client):
    await _create_environment(client, "production")
    body = await gql(
        client,
        CREATE_ENVIRONMENT,
        {"input": {"name": "production"}},
        expect_errors=True,
    )
    assert_that(body, "duplicate name should return errors").contains_key("errors")


async def test_environment_by_id(client):
    env = await _create_environment(client)
    body = await gql(client, ENVIRONMENT, {"id": env["id"]})
    found = body["data"]["environment"]
    assert_that(found["id"], "fetched environment id").is_equal_to(env["id"])
    assert_that(found["name"], "fetched environment name").is_equal_to(env["name"])


async def test_environment_by_id_not_found(client):
    body = await gql(client, ENVIRONMENT, {"id": "00000000-0000-0000-0000-ffffffffffff"})
    assert_that(body["data"]["environment"], "non-existent id should return null").is_none()


async def test_environments_list(client):
    await _create_environment(client, "production")
    await _create_environment(client, "staging")

    body = await gql(client, ENVIRONMENTS)
    edges = body["data"]["environments"]["edges"]
    names = [e["node"]["name"] for e in edges]
    assert_that(names, "environments list").contains("production", "staging")


async def test_environments_excludes_sentinel(client):
    body = await gql(client, ENVIRONMENTS)
    edges = body["data"]["environments"]["edges"]
    names = [e["node"]["name"] for e in edges]
    assert_that(names, "sentinel row should be hidden").does_not_contain("_global")


async def test_update_environment(client):
    env = await _create_environment(client, "production")

    body = await gql(
        client,
        UPDATE_ENVIRONMENT,
        {"input": {"id": env["id"], "description": "prod cluster"}},
    )
    updated = body["data"]["updateEnvironment"]
    assert_that(updated["name"], "name unchanged").is_equal_to("production")
    assert_that(updated["description"], "description updated").is_equal_to("prod cluster")
    assert_that(updated["updatedAt"], "updatedAt advanced").is_greater_than_or_equal_to(env["updatedAt"])


async def test_update_environment_partial(client):
    env = await _create_environment(client, "production", "original description")

    body = await gql(
        client,
        UPDATE_ENVIRONMENT,
        {"input": {"id": env["id"], "name": "prod"}},
    )
    updated = body["data"]["updateEnvironment"]
    assert_that(updated["name"], "name updated").is_equal_to("prod")
    assert_that(updated["description"], "description preserved").is_equal_to("original description")


async def test_update_archived_environment_fails(client):
    env = await _create_environment(client)
    await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})

    body = await gql(
        client,
        UPDATE_ENVIRONMENT,
        {"input": {"id": env["id"], "name": "new-name"}},
        expect_errors=True,
    )
    assert_that(body, "updating archived environment should return errors").contains_key("errors")


async def test_archive_environment(client):
    env = await _create_environment(client)

    body = await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})
    archived = body["data"]["archiveEnvironment"]
    assert_that(archived["archivedAt"], "archivedAt should be set").is_not_none()


async def test_archive_hides_from_list(client):
    env = await _create_environment(client)
    await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})

    body = await gql(client, ENVIRONMENTS)
    edges = body["data"]["environments"]["edges"]
    ids = [e["node"]["id"] for e in edges]
    assert_that(ids, "archived environment hidden from default list").does_not_contain(env["id"])


async def test_include_archived(client):
    env = await _create_environment(client)
    await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})

    body = await gql(client, ENVIRONMENTS, {"includeArchived": True})
    edges = body["data"]["environments"]["edges"]
    ids = [e["node"]["id"] for e in edges]
    assert_that(ids, "archived environment visible with includeArchived").contains(env["id"])


async def test_unarchive_environment(client):
    env = await _create_environment(client)
    await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})

    body = await gql(client, UNARCHIVE_ENVIRONMENT, {"id": env["id"]})
    restored = body["data"]["unarchiveEnvironment"]
    assert_that(restored["archivedAt"], "archivedAt cleared after unarchive").is_none()

    body = await gql(client, ENVIRONMENTS)
    ids = [e["node"]["id"] for e in body["data"]["environments"]["edges"]]
    assert_that(ids, "unarchived environment visible in default list").contains(env["id"])


async def test_search_by_name(client):
    await _create_environment(client, "production", "prod cluster")
    await _create_environment(client, "staging", "staging cluster")

    body = await gql(client, ENVIRONMENTS, {"search": "production"})
    edges = body["data"]["environments"]["edges"]
    assert_that(edges, "search by name result count").is_length(1)
    assert_that(edges[0]["node"]["name"], "matched environment name").is_equal_to("production")


async def test_search_by_description(client):
    await _create_environment(client, "production", "prod cluster")
    await _create_environment(client, "staging", "test environment")

    body = await gql(client, ENVIRONMENTS, {"search": "test environment"})
    edges = body["data"]["environments"]["edges"]
    assert_that(edges, "search by description result count").is_length(1)
    assert_that(edges[0]["node"]["name"], "matched environment name").is_equal_to("staging")


async def test_search_case_insensitive(client):
    await _create_environment(client, "Production")

    body = await gql(client, ENVIRONMENTS, {"search": "production"})
    edges = body["data"]["environments"]["edges"]
    assert_that(edges, "case-insensitive search result count").is_length(1)


async def test_pagination(client):
    for i in range(5):
        await _create_environment(client, f"env-{i:02d}")

    body = await gql(client, ENVIRONMENTS, {"first": 2})
    page1 = body["data"]["environments"]
    assert_that(page1["edges"], "page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"], "page 1 has next page").is_true()

    body = await gql(client, ENVIRONMENTS, {"first": 2, "after": page1["pageInfo"]["endCursor"]})
    page2 = body["data"]["environments"]
    assert_that(page2["edges"], "page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"], "page 2 has next page").is_true()

    body = await gql(client, ENVIRONMENTS, {"first": 2, "after": page2["pageInfo"]["endCursor"]})
    page3 = body["data"]["environments"]
    assert_that(page3["edges"], "page 3 edge count").is_length(1)
    assert_that(page3["pageInfo"]["hasNextPage"], "page 3 has no next page").is_false()


async def test_pagination_with_search(client):
    for i in range(4):
        await _create_environment(client, f"alpha-{i:02d}")
    await _create_environment(client, "beta-00")

    body = await gql(client, ENVIRONMENTS, {"search": "alpha", "first": 2})
    page1 = body["data"]["environments"]
    assert_that(page1["edges"], "search page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"], "search page 1 has next page").is_true()

    body = await gql(
        client, ENVIRONMENTS, {"search": "alpha", "first": 2, "after": page1["pageInfo"]["endCursor"]}
    )
    page2 = body["data"]["environments"]
    assert_that(page2["edges"], "search page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"], "search page 2 has no next page").is_false()


async def test_cursor_invalid_with_changed_search(client):
    for i in range(3):
        await _create_environment(client, f"env-{i:02d}")

    body = await gql(client, ENVIRONMENTS, {"search": "env", "first": 1})
    cursor = body["data"]["environments"]["pageInfo"]["endCursor"]

    body = await gql(
        client,
        ENVIRONMENTS,
        {"search": "other", "first": 1, "after": cursor},
        expect_errors=True,
    )
    assert_that(body, "mismatched search cursor should return errors").contains_key("errors")
