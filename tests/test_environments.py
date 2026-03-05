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
    assert env["name"] == "production"
    assert env["description"] == "prod cluster"
    assert env["id"] is not None
    assert env["createdAt"] is not None
    assert env["updatedAt"] is not None
    assert env["archivedAt"] is None


async def test_create_environment_minimal(client):
    env = await _create_environment(client, "staging")
    assert env["name"] == "staging"
    assert env["description"] is None


async def test_create_environment_duplicate_name(client):
    await _create_environment(client, "production")
    body = await gql(
        client,
        CREATE_ENVIRONMENT,
        {"input": {"name": "production"}},
        expect_errors=True,
    )
    assert "errors" in body


async def test_environment_by_id(client):
    env = await _create_environment(client)
    body = await gql(client, ENVIRONMENT, {"id": env["id"]})
    found = body["data"]["environment"]
    assert found["id"] == env["id"]
    assert found["name"] == env["name"]


async def test_environment_by_id_not_found(client):
    body = await gql(client, ENVIRONMENT, {"id": "00000000-0000-0000-0000-ffffffffffff"})
    assert body["data"]["environment"] is None


async def test_environments_list(client):
    await _create_environment(client, "production")
    await _create_environment(client, "staging")

    body = await gql(client, ENVIRONMENTS)
    edges = body["data"]["environments"]["edges"]
    names = [e["node"]["name"] for e in edges]
    assert "production" in names
    assert "staging" in names


async def test_environments_excludes_sentinel(client):
    body = await gql(client, ENVIRONMENTS)
    edges = body["data"]["environments"]["edges"]
    names = [e["node"]["name"] for e in edges]
    assert "_global" not in names


async def test_update_environment(client):
    env = await _create_environment(client, "production")

    body = await gql(
        client,
        UPDATE_ENVIRONMENT,
        {"input": {"id": env["id"], "description": "prod cluster"}},
    )
    updated = body["data"]["updateEnvironment"]
    assert updated["name"] == "production"
    assert updated["description"] == "prod cluster"
    assert updated["updatedAt"] >= env["updatedAt"]


async def test_update_environment_partial(client):
    env = await _create_environment(client, "production", "original description")

    body = await gql(
        client,
        UPDATE_ENVIRONMENT,
        {"input": {"id": env["id"], "name": "prod"}},
    )
    updated = body["data"]["updateEnvironment"]
    assert updated["name"] == "prod"
    assert updated["description"] == "original description"


async def test_update_archived_environment_fails(client):
    env = await _create_environment(client)
    await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})

    body = await gql(
        client,
        UPDATE_ENVIRONMENT,
        {"input": {"id": env["id"], "name": "new-name"}},
        expect_errors=True,
    )
    assert "errors" in body


async def test_archive_environment(client):
    env = await _create_environment(client)

    body = await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})
    archived = body["data"]["archiveEnvironment"]
    assert archived["archivedAt"] is not None


async def test_archive_hides_from_list(client):
    env = await _create_environment(client)
    await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})

    body = await gql(client, ENVIRONMENTS)
    edges = body["data"]["environments"]["edges"]
    ids = [e["node"]["id"] for e in edges]
    assert env["id"] not in ids


async def test_include_archived(client):
    env = await _create_environment(client)
    await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})

    body = await gql(client, ENVIRONMENTS, {"includeArchived": True})
    edges = body["data"]["environments"]["edges"]
    ids = [e["node"]["id"] for e in edges]
    assert env["id"] in ids


async def test_unarchive_environment(client):
    env = await _create_environment(client)
    await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})

    body = await gql(client, UNARCHIVE_ENVIRONMENT, {"id": env["id"]})
    restored = body["data"]["unarchiveEnvironment"]
    assert restored["archivedAt"] is None

    body = await gql(client, ENVIRONMENTS)
    ids = [e["node"]["id"] for e in body["data"]["environments"]["edges"]]
    assert env["id"] in ids


async def test_search_by_name(client):
    await _create_environment(client, "production", "prod cluster")
    await _create_environment(client, "staging", "staging cluster")

    body = await gql(client, ENVIRONMENTS, {"search": "production"})
    edges = body["data"]["environments"]["edges"]
    assert len(edges) == 1
    assert edges[0]["node"]["name"] == "production"


async def test_search_by_description(client):
    await _create_environment(client, "production", "prod cluster")
    await _create_environment(client, "staging", "test environment")

    body = await gql(client, ENVIRONMENTS, {"search": "test environment"})
    edges = body["data"]["environments"]["edges"]
    assert len(edges) == 1
    assert edges[0]["node"]["name"] == "staging"


async def test_search_case_insensitive(client):
    await _create_environment(client, "Production")

    body = await gql(client, ENVIRONMENTS, {"search": "production"})
    edges = body["data"]["environments"]["edges"]
    assert len(edges) == 1


async def test_pagination(client):
    for i in range(5):
        await _create_environment(client, f"env-{i:02d}")

    body = await gql(client, ENVIRONMENTS, {"first": 2})
    page1 = body["data"]["environments"]
    assert len(page1["edges"]) == 2
    assert page1["pageInfo"]["hasNextPage"] is True

    body = await gql(client, ENVIRONMENTS, {"first": 2, "after": page1["pageInfo"]["endCursor"]})
    page2 = body["data"]["environments"]
    assert len(page2["edges"]) == 2
    assert page2["pageInfo"]["hasNextPage"] is True

    body = await gql(client, ENVIRONMENTS, {"first": 2, "after": page2["pageInfo"]["endCursor"]})
    page3 = body["data"]["environments"]
    assert len(page3["edges"]) == 1
    assert page3["pageInfo"]["hasNextPage"] is False


async def test_pagination_with_search(client):
    for i in range(4):
        await _create_environment(client, f"alpha-{i:02d}")
    await _create_environment(client, "beta-00")

    body = await gql(client, ENVIRONMENTS, {"search": "alpha", "first": 2})
    page1 = body["data"]["environments"]
    assert len(page1["edges"]) == 2
    assert page1["pageInfo"]["hasNextPage"] is True

    body = await gql(
        client, ENVIRONMENTS, {"search": "alpha", "first": 2, "after": page1["pageInfo"]["endCursor"]}
    )
    page2 = body["data"]["environments"]
    assert len(page2["edges"]) == 2
    assert page2["pageInfo"]["hasNextPage"] is False


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
    assert "errors" in body
