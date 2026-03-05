from assertpy import assert_that
from conftest import gql
from utils import create_environment, create_revision, create_service, create_shared_value, nodes, parse_dt

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

# -- Queries --

SHARED_VALUES = """
query SharedValues($includeArchived: Boolean, $first: Int, $after: String) {
    sharedValues(includeArchived: $includeArchived, first: $first, after: $after) {
        edges {
            node { id name createdAt updatedAt archivedAt }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

SEARCH_SHARED_VALUES = """
query SearchSharedValues($search: String!, $includeArchived: Boolean, $limit: Int) {
    searchSharedValues(search: $search, includeArchived: $includeArchived, limit: $limit) {
        id name createdAt updatedAt archivedAt
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
                node { id sharedValue { id } service { id } environment { id } value isCurrent createdAt }
                cursor
            }
            pageInfo { hasNextPage endCursor }
        }
    }
}
"""


# -- Shared Value CRUD Tests --


async def testcreate_shared_value(client):
    sv = await create_shared_value(client, "db_password")
    assert_that(sv["name"]).described_as("shared value name").is_equal_to("db_password")
    assert_that(sv["id"]).described_as("shared value id").is_not_none()
    assert_that(sv["createdAt"]).described_as("createdAt timestamp").is_not_none()
    assert_that(sv["archivedAt"]).described_as(
        "new shared value should not be archived"
    ).is_none()


async def testcreate_shared_value_duplicate_name(client):
    await create_shared_value(client, "db_password")
    body = await gql(
        client,
        CREATE_SHARED_VALUE,
        {"input": {"name": "db_password"}},
        expect_errors=True,
    )
    assert_that(body).described_as("duplicate name should return errors").contains_key("errors")


async def test_shared_value_by_id(client):
    sv = await create_shared_value(client)
    body = await gql(client, SHARED_VALUE, {"id": sv["id"]})
    found = body["data"]["sharedValue"]
    assert_that(found["id"]).described_as("fetched shared value id").is_equal_to(sv["id"])
    assert_that(found["name"]).described_as("fetched shared value name").is_equal_to(sv["name"])


async def test_shared_value_by_id_not_found(client):
    body = await gql(client, SHARED_VALUE, {"id": "00000000-0000-0000-0000-ffffffffffff"})
    assert_that(body["data"]["sharedValue"]).described_as("non-existent id").is_none()


async def test_shared_values_list(client):
    await create_shared_value(client, "db_password")
    await create_shared_value(client, "api_key")

    body = await gql(client, SHARED_VALUES)
    assert_that(nodes(body["data"]["sharedValues"]["edges"])).described_as(
        "shared values list"
    ).extracting("name").contains("db_password", "api_key")


async def test_update_shared_value(client):
    sv = await create_shared_value(client, "db_password")

    body = await gql(
        client,
        UPDATE_SHARED_VALUE,
        {"input": {"id": sv["id"], "name": "db_pass"}},
    )
    updated = body["data"]["updateSharedValue"]
    assert_that(updated["name"]).described_as("name updated").is_equal_to("db_pass")
    assert_that(parse_dt(updated["updatedAt"])).described_as("updatedAt advanced").is_after(
        parse_dt(sv["updatedAt"])
    )


async def test_update_archived_shared_value_fails(client):
    sv = await create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(
        client,
        UPDATE_SHARED_VALUE,
        {"input": {"id": sv["id"], "name": "new_name"}},
        expect_errors=True,
    )
    assert_that(body).described_as("updating archived shared value").contains_key("errors")


async def test_archive_shared_value(client):
    sv = await create_shared_value(client)

    body = await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})
    archived = body["data"]["archiveSharedValue"]
    assert_that(archived["archivedAt"]).described_as("archivedAt should be set").is_not_none()


async def test_archive_hides_from_list(client):
    sv = await create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(client, SHARED_VALUES)
    assert_that(nodes(body["data"]["sharedValues"]["edges"])).described_as(
        "archived shared value hidden from default list"
    ).extracting("id").does_not_contain(sv["id"])


async def test_include_archived(client):
    sv = await create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(client, SHARED_VALUES, {"includeArchived": True})
    assert_that(nodes(body["data"]["sharedValues"]["edges"])).described_as(
        "archived shared value visible with includeArchived"
    ).extracting("id").contains(sv["id"])


async def test_unarchive_shared_value(client):
    sv = await create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(client, UNARCHIVE_SHARED_VALUE, {"id": sv["id"]})
    restored = body["data"]["unarchiveSharedValue"]
    assert_that(restored["archivedAt"]).described_as(
        "archivedAt cleared after unarchive"
    ).is_none()

    body = await gql(client, SHARED_VALUES)
    assert_that(nodes(body["data"]["sharedValues"]["edges"])).described_as(
        "unarchived shared value visible in default list"
    ).extracting("id").contains(sv["id"])


async def test_search_by_name(client):
    await create_shared_value(client, "db_password")
    await create_shared_value(client, "api_key")

    body = await gql(client, SEARCH_SHARED_VALUES, {"search": "db_pass"})
    results = body["data"]["searchSharedValues"]
    assert_that(results).described_as("search by name result count").is_length(1)
    assert_that(results[0]["name"]).described_as("matched shared value name").is_equal_to(
        "db_password"
    )


async def test_search_respects_limit(client):
    """Search should return up to `limit` results."""
    for i in range(5):
        await create_shared_value(client, f"db_val_{i:02d}")
    await create_shared_value(client, "api_key")

    body = await gql(client, SEARCH_SHARED_VALUES, {"search": "db_val", "limit": 3})
    results = body["data"]["searchSharedValues"]
    assert_that(results).described_as("search limited to limit").is_length(3)


async def test_pagination(client):
    for i in range(5):
        await create_shared_value(client, f"val-{i:02d}")

    body = await gql(client, SHARED_VALUES, {"first": 2})
    page1 = body["data"]["sharedValues"]
    assert_that(page1["edges"]).described_as("page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as("page 1 has next page").is_true()

    body = await gql(client, SHARED_VALUES, {"first": 2, "after": page1["pageInfo"]["endCursor"]})
    page2 = body["data"]["sharedValues"]
    assert_that(page2["edges"]).described_as("page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as("page 2 has next page").is_true()

    body = await gql(client, SHARED_VALUES, {"first": 2, "after": page2["pageInfo"]["endCursor"]})
    page3 = body["data"]["sharedValues"]
    assert_that(page3["edges"]).described_as("page 3 edge count").is_length(1)
    assert_that(page3["pageInfo"]["hasNextPage"]).described_as(
        "page 3 has no next page"
    ).is_false()


# -- Revision Tests --


async def test_create_revision(client):
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env = await create_environment(client)

    rev = await create_revision(client, sv["id"], svc["id"], env["id"], "secret123")
    assert_that(rev["sharedValue"]["id"]).described_as("revision shared value id").is_equal_to(
        sv["id"]
    )
    assert_that(rev["service"]["id"]).described_as("revision service id").is_equal_to(svc["id"])
    assert_that(rev["environment"]["id"]).described_as("revision environment id").is_equal_to(
        env["id"]
    )
    assert_that(rev["value"]).described_as("revision value").is_equal_to("secret123")
    assert_that(rev["isCurrent"]).described_as("new revision should be current").is_true()


async def test_new_revision_replaces_current(client):
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env = await create_environment(client)

    rev1 = await create_revision(client, sv["id"], svc["id"], env["id"], "v1")
    rev2 = await create_revision(client, sv["id"], svc["id"], env["id"], "v2")

    assert_that(rev2["isCurrent"]).described_as("newest revision should be current").is_true()

    # Check all revisions — rev1 should no longer be current
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"]})
    revisions = body["data"]["sharedValue"]["revisions"]["edges"]
    by_id = {e["node"]["id"]: e["node"] for e in revisions}
    assert_that(by_id[rev1["id"]]["isCurrent"]).described_as(
        "old revision no longer current"
    ).is_false()
    assert_that(by_id[rev2["id"]]["isCurrent"]).described_as(
        "new revision is current"
    ).is_true()


async def test_revisions_scoped_by_service_and_environment(client):
    sv = await create_shared_value(client)
    svc1 = await create_service(client, "traefik")
    svc2 = await create_service(client, "nginx")
    env = await create_environment(client)

    await create_revision(client, sv["id"], svc1["id"], env["id"], "val-svc1")
    await create_revision(client, sv["id"], svc2["id"], env["id"], "val-svc2")

    # Filter by svc1
    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "serviceId": svc1["id"]}
    )
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
    assert_that(revisions).described_as("revisions filtered by svc1").is_length(1)
    assert_that(revisions).extracting("value").described_as(
        "svc1 revision value"
    ).contains("val-svc1")

    # Filter by svc2
    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "serviceId": svc2["id"]}
    )
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
    assert_that(revisions).described_as("revisions filtered by svc2").is_length(1)
    assert_that(revisions).extracting("value").described_as(
        "svc2 revision value"
    ).contains("val-svc2")


async def test_revisions_current_only_filter(client):
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env = await create_environment(client)

    await create_revision(client, sv["id"], svc["id"], env["id"], "v1")
    await create_revision(client, sv["id"], svc["id"], env["id"], "v2")

    # All revisions
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"]})
    all_revs = body["data"]["sharedValue"]["revisions"]["edges"]
    assert_that(all_revs).described_as("all revisions count").is_length(2)

    # Current only
    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "currentOnly": True}
    )
    current_revs = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
    assert_that(current_revs).described_as("current-only revisions count").is_length(1)
    assert_that(current_revs).extracting("value").described_as(
        "current revision value"
    ).contains("v2")
    assert_that(current_revs).extracting("isCurrent").described_as(
        "current revision flag"
    ).contains(True)


async def test_revisions_pagination(client):
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env = await create_environment(client)

    for i in range(5):
        await create_revision(client, sv["id"], svc["id"], env["id"], f"v{i}")

    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "first": 2}
    )
    page1 = body["data"]["sharedValue"]["revisions"]
    assert_that(page1["edges"]).described_as("revision page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as(
        "revision page 1 has next page"
    ).is_true()

    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS,
        {"id": sv["id"], "first": 2, "after": page1["pageInfo"]["endCursor"]},
    )
    page2 = body["data"]["sharedValue"]["revisions"]
    assert_that(page2["edges"]).described_as("revision page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as(
        "revision page 2 has next page"
    ).is_true()

    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS,
        {"id": sv["id"], "first": 2, "after": page2["pageInfo"]["endCursor"]},
    )
    page3 = body["data"]["sharedValue"]["revisions"]
    assert_that(page3["edges"]).described_as("revision page 3 edge count").is_length(1)
    assert_that(page3["pageInfo"]["hasNextPage"]).described_as(
        "revision page 3 has no next page"
    ).is_false()


async def test_revisions_filter_by_environment(client):
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env1 = await create_environment(client, "production")
    env2 = await create_environment(client, "staging")

    await create_revision(client, sv["id"], svc["id"], env1["id"], "prod-val")
    await create_revision(client, sv["id"], svc["id"], env2["id"], "staging-val")

    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "environmentId": env1["id"]}
    )
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
    assert_that(revisions).described_as("revisions filtered by production env").is_length(1)
    assert_that(revisions).extracting("value").described_as(
        "production revision value"
    ).contains("prod-val")


async def testcreate_shared_value_with_percent_in_name_fails(client):
    body = await gql(
        client, CREATE_SHARED_VALUE, {"input": {"name": "bad%name"}}, expect_errors=True
    )
    assert_that(body).described_as("percent in name rejected").contains_key("errors")


async def testcreate_shared_value_with_backslash_in_name_fails(client):
    body = await gql(
        client, CREATE_SHARED_VALUE, {"input": {"name": "bad\\name"}}, expect_errors=True
    )
    assert_that(body).described_as("backslash in name rejected").contains_key("errors")


async def test_update_shared_value_with_percent_in_name_fails(client):
    sv = await create_shared_value(client)
    body = await gql(
        client,
        UPDATE_SHARED_VALUE,
        {"input": {"id": sv["id"], "name": "bad%name"}},
        expect_errors=True,
    )
    assert_that(body).described_as("percent in update name rejected").contains_key("errors")


async def test_shared_value_name_with_underscore_allowed(client):
    sv = await create_shared_value(client, "my_value")
    assert_that(sv["name"]).described_as("underscore in name").is_equal_to("my_value")
