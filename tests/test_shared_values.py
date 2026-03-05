from assertpy import assert_that
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
    assert_that(sv["name"], "shared value name").is_equal_to("db_password")
    assert_that(sv["id"], "shared value id").is_not_none()
    assert_that(sv["createdAt"], "createdAt timestamp").is_not_none()
    assert_that(sv["archivedAt"], "new shared value should not be archived").is_none()


async def test_create_shared_value_duplicate_name(client):
    await _create_shared_value(client, "db_password")
    body = await gql(
        client,
        CREATE_SHARED_VALUE,
        {"input": {"name": "db_password"}},
        expect_errors=True,
    )
    assert_that(body, "duplicate name should return errors").contains_key("errors")


async def test_shared_value_by_id(client):
    sv = await _create_shared_value(client)
    body = await gql(client, SHARED_VALUE, {"id": sv["id"]})
    found = body["data"]["sharedValue"]
    assert_that(found["id"], "fetched shared value id").is_equal_to(sv["id"])
    assert_that(found["name"], "fetched shared value name").is_equal_to(sv["name"])


async def test_shared_value_by_id_not_found(client):
    body = await gql(client, SHARED_VALUE, {"id": "00000000-0000-0000-0000-ffffffffffff"})
    assert_that(body["data"]["sharedValue"], "non-existent id should return null").is_none()


async def test_shared_values_list(client):
    await _create_shared_value(client, "db_password")
    await _create_shared_value(client, "api_key")

    body = await gql(client, SHARED_VALUES)
    edges = body["data"]["sharedValues"]["edges"]
    names = [e["node"]["name"] for e in edges]
    assert_that(names, "shared values list").contains("db_password", "api_key")


async def test_update_shared_value(client):
    sv = await _create_shared_value(client, "db_password")

    body = await gql(
        client,
        UPDATE_SHARED_VALUE,
        {"input": {"id": sv["id"], "name": "db_pass"}},
    )
    updated = body["data"]["updateSharedValue"]
    assert_that(updated["name"], "name updated").is_equal_to("db_pass")
    assert_that(updated["updatedAt"], "updatedAt advanced").is_greater_than_or_equal_to(sv["updatedAt"])


async def test_update_archived_shared_value_fails(client):
    sv = await _create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(
        client,
        UPDATE_SHARED_VALUE,
        {"input": {"id": sv["id"], "name": "new_name"}},
        expect_errors=True,
    )
    assert_that(body, "updating archived shared value should return errors").contains_key("errors")


async def test_archive_shared_value(client):
    sv = await _create_shared_value(client)

    body = await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})
    archived = body["data"]["archiveSharedValue"]
    assert_that(archived["archivedAt"], "archivedAt should be set").is_not_none()


async def test_archive_hides_from_list(client):
    sv = await _create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(client, SHARED_VALUES)
    ids = [e["node"]["id"] for e in body["data"]["sharedValues"]["edges"]]
    assert_that(ids, "archived shared value hidden from default list").does_not_contain(sv["id"])


async def test_include_archived(client):
    sv = await _create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(client, SHARED_VALUES, {"includeArchived": True})
    ids = [e["node"]["id"] for e in body["data"]["sharedValues"]["edges"]]
    assert_that(ids, "archived shared value visible with includeArchived").contains(sv["id"])


async def test_unarchive_shared_value(client):
    sv = await _create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(client, UNARCHIVE_SHARED_VALUE, {"id": sv["id"]})
    restored = body["data"]["unarchiveSharedValue"]
    assert_that(restored["archivedAt"], "archivedAt cleared after unarchive").is_none()

    body = await gql(client, SHARED_VALUES)
    ids = [e["node"]["id"] for e in body["data"]["sharedValues"]["edges"]]
    assert_that(ids, "unarchived shared value visible in default list").contains(sv["id"])


async def test_search_by_name(client):
    await _create_shared_value(client, "db_password")
    await _create_shared_value(client, "api_key")

    body = await gql(client, SHARED_VALUES, {"search": "db_pass"})
    edges = body["data"]["sharedValues"]["edges"]
    assert_that(edges, "search by name result count").is_length(1)
    assert_that(edges[0]["node"]["name"], "matched shared value name").is_equal_to("db_password")


async def test_pagination(client):
    for i in range(5):
        await _create_shared_value(client, f"val-{i:02d}")

    body = await gql(client, SHARED_VALUES, {"first": 2})
    page1 = body["data"]["sharedValues"]
    assert_that(page1["edges"], "page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"], "page 1 has next page").is_true()

    body = await gql(client, SHARED_VALUES, {"first": 2, "after": page1["pageInfo"]["endCursor"]})
    page2 = body["data"]["sharedValues"]
    assert_that(page2["edges"], "page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"], "page 2 has next page").is_true()

    body = await gql(client, SHARED_VALUES, {"first": 2, "after": page2["pageInfo"]["endCursor"]})
    page3 = body["data"]["sharedValues"]
    assert_that(page3["edges"], "page 3 edge count").is_length(1)
    assert_that(page3["pageInfo"]["hasNextPage"], "page 3 has no next page").is_false()


# -- Revision Tests --


async def test_create_revision(client):
    sv = await _create_shared_value(client)
    svc = await _create_service(client)
    env = await _create_environment(client)

    rev = await _create_revision(client, sv["id"], svc["id"], env["id"], "secret123")
    assert_that(rev["sharedValue"]["id"], "revision shared value id").is_equal_to(sv["id"])
    assert_that(rev["serviceId"]["id"], "revision service id").is_equal_to(svc["id"])
    assert_that(rev["environmentId"]["id"], "revision environment id").is_equal_to(env["id"])
    assert_that(rev["value"], "revision value").is_equal_to("secret123")
    assert_that(rev["isCurrent"], "new revision should be current").is_true()


async def test_new_revision_replaces_current(client):
    sv = await _create_shared_value(client)
    svc = await _create_service(client)
    env = await _create_environment(client)

    rev1 = await _create_revision(client, sv["id"], svc["id"], env["id"], "v1")
    rev2 = await _create_revision(client, sv["id"], svc["id"], env["id"], "v2")

    assert_that(rev2["isCurrent"], "newest revision should be current").is_true()

    # Check all revisions — rev1 should no longer be current
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"]})
    revisions = body["data"]["sharedValue"]["revisions"]["edges"]
    by_id = {e["node"]["id"]: e["node"] for e in revisions}
    assert_that(by_id[rev1["id"]]["isCurrent"], "old revision no longer current").is_false()
    assert_that(by_id[rev2["id"]]["isCurrent"], "new revision is current").is_true()


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
    assert_that(revisions, "revisions filtered by svc1").is_length(1)
    assert_that(revisions[0]["node"]["value"], "svc1 revision value").is_equal_to("val-svc1")

    # Filter by svc2
    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "serviceId": svc2["id"]}
    )
    revisions = body["data"]["sharedValue"]["revisions"]["edges"]
    assert_that(revisions, "revisions filtered by svc2").is_length(1)
    assert_that(revisions[0]["node"]["value"], "svc2 revision value").is_equal_to("val-svc2")


async def test_revisions_current_only_filter(client):
    sv = await _create_shared_value(client)
    svc = await _create_service(client)
    env = await _create_environment(client)

    await _create_revision(client, sv["id"], svc["id"], env["id"], "v1")
    await _create_revision(client, sv["id"], svc["id"], env["id"], "v2")

    # All revisions
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"]})
    all_revs = body["data"]["sharedValue"]["revisions"]["edges"]
    assert_that(all_revs, "all revisions count").is_length(2)

    # Current only
    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "currentOnly": True}
    )
    current_revs = body["data"]["sharedValue"]["revisions"]["edges"]
    assert_that(current_revs, "current-only revisions count").is_length(1)
    assert_that(current_revs[0]["node"]["value"], "current revision value").is_equal_to("v2")
    assert_that(current_revs[0]["node"]["isCurrent"], "current revision flag").is_true()


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
    assert_that(page1["edges"], "revision page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"], "revision page 1 has next page").is_true()

    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS,
        {"id": sv["id"], "first": 2, "after": page1["pageInfo"]["endCursor"]},
    )
    page2 = body["data"]["sharedValue"]["revisions"]
    assert_that(page2["edges"], "revision page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"], "revision page 2 has next page").is_true()

    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS,
        {"id": sv["id"], "first": 2, "after": page2["pageInfo"]["endCursor"]},
    )
    page3 = body["data"]["sharedValue"]["revisions"]
    assert_that(page3["edges"], "revision page 3 edge count").is_length(1)
    assert_that(page3["pageInfo"]["hasNextPage"], "revision page 3 has no next page").is_false()


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
    assert_that(revisions, "revisions filtered by production env").is_length(1)
    assert_that(revisions[0]["node"]["value"], "production revision value").is_equal_to("prod-val")
