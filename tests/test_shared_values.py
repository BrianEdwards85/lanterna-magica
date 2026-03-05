from conftest import gql

# -- Mutations --

CREATE_SHARED_VALUE = """
mutation CreateSharedValue($input: CreateSharedValueInput!) {
    createSharedValue(input: $input) {
        id name createdAt updatedAt archivedAt
    }
}
"""

UPDATE_SHARED_VALUE = """
mutation UpdateSharedValue($input: UpdateSharedValueInput!) {
    updateSharedValue(input: $input) {
        id name createdAt updatedAt archivedAt
    }
}
"""

ARCHIVE_SHARED_VALUE = """
mutation ArchiveSharedValue($id: ID!) {
    archiveSharedValue(id: $id) {
        id name archivedAt
    }
}
"""

UNARCHIVE_SHARED_VALUE = """
mutation UnarchiveSharedValue($id: ID!) {
    unarchiveSharedValue(id: $id) {
        id name archivedAt
    }
}
"""

CREATE_REVISION = """
mutation CreateSharedValueRevision($input: CreateSharedValueRevisionInput!) {
    createSharedValueRevision(input: $input) {
        id sharedValue { id } serviceId { id } environmentId { id } value isCurrent createdAt
    }
}
"""

CREATE_SERVICE = """
mutation CreateService($input: CreateServiceInput!) {
    createService(input: $input) { id name }
}
"""

CREATE_ENVIRONMENT = """
mutation CreateEnvironment($input: CreateEnvironmentInput!) {
    createEnvironment(input: $input) { id name }
}
"""

# -- Queries --

SHARED_VALUES = """
query SharedValues($includeArchived: Boolean, $first: Int, $after: String, $search: String) {
    sharedValues(includeArchived: $includeArchived, first: $first, after: $after, search: $search) {
        edges {
            node { id name createdAt updatedAt archivedAt }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

SHARED_VALUE = """
query SharedValue($id: ID!) {
    sharedValue(id: $id) {
        id name createdAt updatedAt archivedAt
    }
}
"""

SHARED_VALUE_WITH_REVISIONS = """
query SharedValueWithRevisions(
    $id: ID!,
    $serviceId: ID,
    $environmentId: ID,
    $currentOnly: Boolean,
    $first: Int,
    $after: String
) {
    sharedValue(id: $id) {
        id name
        revisions(
            serviceId: $serviceId,
            environmentId: $environmentId,
            currentOnly: $currentOnly,
            first: $first,
            after: $after
        ) {
            edges {
                node { id sharedValue { id } serviceId { id } environmentId { id } value isCurrent createdAt }
                cursor
            }
            pageInfo { hasNextPage endCursor }
        }
    }
}
"""


# -- Helpers --


async def _create_shared_value(client, name="db_password"):
    body = await gql(client, CREATE_SHARED_VALUE, {"input": {"name": name}})
    return body["data"]["createSharedValue"]


async def _create_service(client, name="traefik"):
    body = await gql(client, CREATE_SERVICE, {"input": {"name": name}})
    return body["data"]["createService"]


async def _create_environment(client, name="production"):
    body = await gql(client, CREATE_ENVIRONMENT, {"input": {"name": name}})
    return body["data"]["createEnvironment"]


async def _create_revision(client, shared_value_id, service_id, environment_id, value):
    body = await gql(
        client,
        CREATE_REVISION,
        {
            "input": {
                "sharedValueId": shared_value_id,
                "serviceId": service_id,
                "environmentId": environment_id,
                "value": value,
            }
        },
    )
    return body["data"]["createSharedValueRevision"]


# -- Shared Value CRUD Tests --


async def test_create_shared_value(client):
    sv = await _create_shared_value(client, "db_password")
    assert sv["name"] == "db_password"
    assert sv["id"] is not None
    assert sv["createdAt"] is not None
    assert sv["archivedAt"] is None


async def test_create_shared_value_duplicate_name(client):
    await _create_shared_value(client, "db_password")
    body = await gql(
        client,
        CREATE_SHARED_VALUE,
        {"input": {"name": "db_password"}},
        expect_errors=True,
    )
    assert "errors" in body


async def test_shared_value_by_id(client):
    sv = await _create_shared_value(client)
    body = await gql(client, SHARED_VALUE, {"id": sv["id"]})
    found = body["data"]["sharedValue"]
    assert found["id"] == sv["id"]
    assert found["name"] == sv["name"]


async def test_shared_value_by_id_not_found(client):
    body = await gql(client, SHARED_VALUE, {"id": "00000000-0000-0000-0000-ffffffffffff"})
    assert body["data"]["sharedValue"] is None


async def test_shared_values_list(client):
    await _create_shared_value(client, "db_password")
    await _create_shared_value(client, "api_key")

    body = await gql(client, SHARED_VALUES)
    edges = body["data"]["sharedValues"]["edges"]
    names = [e["node"]["name"] for e in edges]
    assert "db_password" in names
    assert "api_key" in names


async def test_update_shared_value(client):
    sv = await _create_shared_value(client, "db_password")

    body = await gql(
        client,
        UPDATE_SHARED_VALUE,
        {"input": {"id": sv["id"], "name": "db_pass"}},
    )
    updated = body["data"]["updateSharedValue"]
    assert updated["name"] == "db_pass"
    assert updated["updatedAt"] >= sv["updatedAt"]


async def test_update_archived_shared_value_fails(client):
    sv = await _create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(
        client,
        UPDATE_SHARED_VALUE,
        {"input": {"id": sv["id"], "name": "new_name"}},
        expect_errors=True,
    )
    assert "errors" in body


async def test_archive_shared_value(client):
    sv = await _create_shared_value(client)

    body = await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})
    archived = body["data"]["archiveSharedValue"]
    assert archived["archivedAt"] is not None


async def test_archive_hides_from_list(client):
    sv = await _create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(client, SHARED_VALUES)
    ids = [e["node"]["id"] for e in body["data"]["sharedValues"]["edges"]]
    assert sv["id"] not in ids


async def test_include_archived(client):
    sv = await _create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(client, SHARED_VALUES, {"includeArchived": True})
    ids = [e["node"]["id"] for e in body["data"]["sharedValues"]["edges"]]
    assert sv["id"] in ids


async def test_unarchive_shared_value(client):
    sv = await _create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(client, UNARCHIVE_SHARED_VALUE, {"id": sv["id"]})
    restored = body["data"]["unarchiveSharedValue"]
    assert restored["archivedAt"] is None

    body = await gql(client, SHARED_VALUES)
    ids = [e["node"]["id"] for e in body["data"]["sharedValues"]["edges"]]
    assert sv["id"] in ids


async def test_search_by_name(client):
    await _create_shared_value(client, "db_password")
    await _create_shared_value(client, "api_key")

    body = await gql(client, SHARED_VALUES, {"search": "db_pass"})
    edges = body["data"]["sharedValues"]["edges"]
    assert len(edges) == 1
    assert edges[0]["node"]["name"] == "db_password"


async def test_pagination(client):
    for i in range(5):
        await _create_shared_value(client, f"val-{i:02d}")

    body = await gql(client, SHARED_VALUES, {"first": 2})
    page1 = body["data"]["sharedValues"]
    assert len(page1["edges"]) == 2
    assert page1["pageInfo"]["hasNextPage"] is True

    body = await gql(client, SHARED_VALUES, {"first": 2, "after": page1["pageInfo"]["endCursor"]})
    page2 = body["data"]["sharedValues"]
    assert len(page2["edges"]) == 2
    assert page2["pageInfo"]["hasNextPage"] is True

    body = await gql(client, SHARED_VALUES, {"first": 2, "after": page2["pageInfo"]["endCursor"]})
    page3 = body["data"]["sharedValues"]
    assert len(page3["edges"]) == 1
    assert page3["pageInfo"]["hasNextPage"] is False


# -- Revision Tests --


async def test_create_revision(client):
    sv = await _create_shared_value(client)
    svc = await _create_service(client)
    env = await _create_environment(client)

    rev = await _create_revision(client, sv["id"], svc["id"], env["id"], "secret123")
    assert rev["sharedValue"]["id"] == sv["id"]
    assert rev["serviceId"]["id"] == svc["id"]
    assert rev["environmentId"]["id"] == env["id"]
    assert rev["value"] == "secret123"
    assert rev["isCurrent"] is True


async def test_new_revision_replaces_current(client):
    sv = await _create_shared_value(client)
    svc = await _create_service(client)
    env = await _create_environment(client)

    rev1 = await _create_revision(client, sv["id"], svc["id"], env["id"], "v1")
    rev2 = await _create_revision(client, sv["id"], svc["id"], env["id"], "v2")

    assert rev2["isCurrent"] is True

    # Check all revisions — rev1 should no longer be current
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"]})
    revisions = body["data"]["sharedValue"]["revisions"]["edges"]
    by_id = {e["node"]["id"]: e["node"] for e in revisions}
    assert by_id[rev1["id"]]["isCurrent"] is False
    assert by_id[rev2["id"]]["isCurrent"] is True


async def test_revisions_scoped_by_service_and_environment(client):
    sv = await _create_shared_value(client)
    svc1 = await _create_service(client, "traefik")
    svc2 = await _create_service(client, "nginx")
    env = await _create_environment(client)

    await _create_revision(client, sv["id"], svc1["id"], env["id"], "val-svc1")
    await _create_revision(client, sv["id"], svc2["id"], env["id"], "val-svc2")

    # Filter by svc1
    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "serviceId": svc1["id"]}
    )
    revisions = body["data"]["sharedValue"]["revisions"]["edges"]
    assert len(revisions) == 1
    assert revisions[0]["node"]["value"] == "val-svc1"

    # Filter by svc2
    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "serviceId": svc2["id"]}
    )
    revisions = body["data"]["sharedValue"]["revisions"]["edges"]
    assert len(revisions) == 1
    assert revisions[0]["node"]["value"] == "val-svc2"


async def test_revisions_current_only_filter(client):
    sv = await _create_shared_value(client)
    svc = await _create_service(client)
    env = await _create_environment(client)

    await _create_revision(client, sv["id"], svc["id"], env["id"], "v1")
    await _create_revision(client, sv["id"], svc["id"], env["id"], "v2")

    # All revisions
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"]})
    all_revs = body["data"]["sharedValue"]["revisions"]["edges"]
    assert len(all_revs) == 2

    # Current only
    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "currentOnly": True}
    )
    current_revs = body["data"]["sharedValue"]["revisions"]["edges"]
    assert len(current_revs) == 1
    assert current_revs[0]["node"]["value"] == "v2"
    assert current_revs[0]["node"]["isCurrent"] is True


async def test_revisions_pagination(client):
    sv = await _create_shared_value(client)
    svc = await _create_service(client)
    env = await _create_environment(client)

    for i in range(5):
        await _create_revision(client, sv["id"], svc["id"], env["id"], f"v{i}")

    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "first": 2}
    )
    page1 = body["data"]["sharedValue"]["revisions"]
    assert len(page1["edges"]) == 2
    assert page1["pageInfo"]["hasNextPage"] is True

    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS,
        {"id": sv["id"], "first": 2, "after": page1["pageInfo"]["endCursor"]},
    )
    page2 = body["data"]["sharedValue"]["revisions"]
    assert len(page2["edges"]) == 2
    assert page2["pageInfo"]["hasNextPage"] is True

    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS,
        {"id": sv["id"], "first": 2, "after": page2["pageInfo"]["endCursor"]},
    )
    page3 = body["data"]["sharedValue"]["revisions"]
    assert len(page3["edges"]) == 1
    assert page3["pageInfo"]["hasNextPage"] is False


async def test_revisions_filter_by_environment(client):
    sv = await _create_shared_value(client)
    svc = await _create_service(client)
    env1 = await _create_environment(client, "production")
    env2 = await _create_environment(client, "staging")

    await _create_revision(client, sv["id"], svc["id"], env1["id"], "prod-val")
    await _create_revision(client, sv["id"], svc["id"], env2["id"], "staging-val")

    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "environmentId": env1["id"]}
    )
    revisions = body["data"]["sharedValue"]["revisions"]["edges"]
    assert len(revisions) == 1
    assert revisions[0]["node"]["value"] == "prod-val"
