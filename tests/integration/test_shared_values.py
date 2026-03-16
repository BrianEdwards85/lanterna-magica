from assertpy import assert_that
from conftest import gql
from utils import (
    create_dimension_type,
    create_environment,
    create_revision,
    create_service,
    create_shared_value,
    nodes,
    parse_dt,
)

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

SHARED_VALUES_WITH_SEARCH = """
query SharedValuesWithSearch($search: String, $includeArchived: Boolean, $first: Int, $after: String) {
    sharedValues(search: $search, includeArchived: $includeArchived, first: $first, after: $after) {
        edges {
            node { id name createdAt updatedAt archivedAt }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

SHARED_VALUES_BY_IDS = """
query SharedValuesByIds($ids: [ID!]!) {
    sharedValuesByIds(ids: $ids) {
        id name createdAt updatedAt archivedAt
    }
}
"""

SHARED_VALUE_WITH_REVISIONS = """
query SharedValueWithRevisions(
    $ids: [ID!]!,
    $dimensionIds: [ID!],
    $currentOnly: Boolean,
    $first: Int,
    $after: String
) {
    sharedValuesByIds(ids: $ids) {
        id name
        revisions(
            dimensionIds: $dimensionIds,
            currentOnly: $currentOnly,
            first: $first,
            after: $after
        ) {
            edges {
                node { id sharedValue { id } dimensions { id name } value isCurrent createdAt }
                cursor
            }
            pageInfo { hasNextPage endCursor }
        }
    }
}
"""

SHARED_VALUE_WITH_REVISIONS_INCLUDE_BASE = """
query SharedValueWithRevisionsIncludeBase(
    $ids: [ID!]!,
    $dimensionIds: [ID!],
    $includeBase: Boolean,
    $currentOnly: Boolean,
    $first: Int,
    $after: String
) {
    sharedValuesByIds(ids: $ids) {
        id name
        revisions(
            dimensionIds: $dimensionIds,
            includeBase: $includeBase,
            currentOnly: $currentOnly,
            first: $first,
            after: $after
        ) {
            edges {
                node { id sharedValue { id } dimensions { id name } value isCurrent createdAt }
                cursor
            }
            pageInfo { hasNextPage endCursor }
        }
    }
}
"""


# -- Shared Value CRUD Tests --


async def test_create_shared_value(client):
    sv = await create_shared_value(client, "db_password")
    assert_that(sv["name"]).described_as("shared value name").is_equal_to("db_password")
    assert_that(sv["id"]).described_as("shared value id").is_not_none()
    assert_that(sv["createdAt"]).described_as("createdAt timestamp").is_not_none()
    assert_that(sv["archivedAt"]).described_as(
        "new shared value should not be archived"
    ).is_none()


async def test_create_shared_value_duplicate_name(client):
    await create_shared_value(client, "db_password")
    body = await gql(
        client,
        CREATE_SHARED_VALUE,
        {"input": {"name": "db_password"}},
        expect_errors=True,
    )
    assert_that(body).described_as("duplicate name should return errors").contains_key(
        "errors"
    )


async def test_shared_values_by_ids(client):
    sv = await create_shared_value(client)
    body = await gql(client, SHARED_VALUES_BY_IDS, {"ids": [sv["id"]]})
    results = body["data"]["sharedValuesByIds"]
    assert_that(results).described_as("returns one result").is_length(1)
    found = results[0]
    assert_that(found["id"]).described_as("fetched shared value id").is_equal_to(
        sv["id"]
    )
    assert_that(found["name"]).described_as("fetched shared value name").is_equal_to(
        sv["name"]
    )


async def test_shared_values_by_ids_multiple(client):
    sv1 = await create_shared_value(client, "db_password")
    sv2 = await create_shared_value(client, "api_key")

    body = await gql(client, SHARED_VALUES_BY_IDS, {"ids": [sv1["id"], sv2["id"]]})
    found = body["data"]["sharedValuesByIds"]
    assert_that(found).described_as("fetched shared values count").is_length(2)
    ids = [sv["id"] for sv in found]
    assert_that(ids).described_as("fetched shared value ids").contains(
        sv1["id"], sv2["id"]
    )


async def test_shared_values_by_ids_unknown_returns_empty(client):
    body = await gql(
        client, SHARED_VALUES_BY_IDS, {"ids": ["00000000-0000-0000-0000-ffffffffffff"]}
    )
    assert_that(body["data"]["sharedValuesByIds"]).described_as(
        "non-existent id returns empty list"
    ).is_empty()


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
    assert_that(parse_dt(updated["updatedAt"])).described_as(
        "updatedAt advanced"
    ).is_after(parse_dt(sv["updatedAt"]))


async def test_update_shared_value_no_fields_fails(client):
    sv = await create_shared_value(client)
    body = await gql(
        client,
        UPDATE_SHARED_VALUE,
        {"input": {"id": sv["id"]}},
        expect_errors=True,
    )
    assert_that(body).described_as("no-op update rejected").contains_key("errors")


async def test_update_archived_shared_value_fails(client):
    sv = await create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(
        client,
        UPDATE_SHARED_VALUE,
        {"input": {"id": sv["id"], "name": "new_name"}},
        expect_errors=True,
    )
    assert_that(body).described_as("updating archived shared value").contains_key(
        "errors"
    )


async def test_archive_shared_value(client):
    sv = await create_shared_value(client)

    body = await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})
    archived = body["data"]["archiveSharedValue"]
    assert_that(archived["archivedAt"]).described_as(
        "archivedAt should be set"
    ).is_not_none()


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

    body = await gql(client, SHARED_VALUES_WITH_SEARCH, {"search": "db_pass"})
    results = nodes(body["data"]["sharedValues"]["edges"])
    assert_that(results).described_as("search by name result count").is_length(1)
    assert_that(results[0]["name"]).described_as(
        "matched shared value name"
    ).is_equal_to("db_password")


async def test_search_respects_pagination(client):
    """Search should respect first/after pagination."""
    for i in range(5):
        await create_shared_value(client, f"db_val_{i:02d}")
    await create_shared_value(client, "api_key")

    body = await gql(client, SHARED_VALUES_WITH_SEARCH, {"search": "db_val", "first": 3})
    page = body["data"]["sharedValues"]
    results = nodes(page["edges"])
    assert_that(results).described_as("search limited to first").is_length(3)
    assert_that(page["pageInfo"]["hasNextPage"]).described_as(
        "more search results available"
    ).is_true()


async def test_pagination(client):
    for i in range(5):
        await create_shared_value(client, f"val-{i:02d}")

    body = await gql(client, SHARED_VALUES, {"first": 2})
    page1 = body["data"]["sharedValues"]
    assert_that(page1["edges"]).described_as("page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as(
        "page 1 has next page"
    ).is_true()

    body = await gql(
        client, SHARED_VALUES, {"first": 2, "after": page1["pageInfo"]["endCursor"]}
    )
    page2 = body["data"]["sharedValues"]
    assert_that(page2["edges"]).described_as("page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as(
        "page 2 has next page"
    ).is_true()

    body = await gql(
        client, SHARED_VALUES, {"first": 2, "after": page2["pageInfo"]["endCursor"]}
    )
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

    rev = await create_revision(client, sv["id"], [svc["id"], env["id"]], "secret123")
    assert_that(rev["sharedValue"]["id"]).described_as(
        "revision shared value id"
    ).is_equal_to(sv["id"])
    dim_ids = [d["id"] for d in rev["dimensions"]]
    assert_that(dim_ids).described_as("revision dimension ids").contains(
        svc["id"], env["id"]
    )
    assert_that(rev["value"]).described_as("revision value").is_equal_to("secret123")
    assert_that(rev["isCurrent"]).described_as(
        "new revision should be current"
    ).is_true()


async def test_new_revision_replaces_current(client):
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env = await create_environment(client)

    rev1 = await create_revision(client, sv["id"], [svc["id"], env["id"]], "v1")
    rev2 = await create_revision(client, sv["id"], [svc["id"], env["id"]], "v2")

    assert_that(rev2["isCurrent"]).described_as(
        "newest revision should be current"
    ).is_true()

    # Check all revisions — rev1 should no longer be current
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]]})
    revisions = body["data"]["sharedValuesByIds"][0]["revisions"]["edges"]
    by_id = {e["node"]["id"]: e["node"] for e in revisions}
    assert_that(by_id[rev1["id"]]["isCurrent"]).described_as(
        "old revision no longer current"
    ).is_false()
    assert_that(by_id[rev2["id"]]["isCurrent"]).described_as(
        "new revision is current"
    ).is_true()


async def test_revisions_scoped_by_dimension(client):
    sv = await create_shared_value(client)
    svc1 = await create_service(client, "traefik")
    svc2 = await create_service(client, "nginx")
    env = await create_environment(client)

    await create_revision(client, sv["id"], [svc1["id"], env["id"]], "val-svc1")
    await create_revision(client, sv["id"], [svc2["id"], env["id"]], "val-svc2")

    # Filter by svc1
    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS,
        {"ids": [sv["id"]], "dimensionIds": [svc1["id"]]},
    )
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    assert_that(revisions).described_as("revisions filtered by svc1").is_length(1)
    assert_that(revisions).extracting("value").described_as(
        "svc1 revision value"
    ).contains("val-svc1")

    # Filter by svc2
    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS,
        {"ids": [sv["id"]], "dimensionIds": [svc2["id"]]},
    )
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    assert_that(revisions).described_as("revisions filtered by svc2").is_length(1)
    assert_that(revisions).extracting("value").described_as(
        "svc2 revision value"
    ).contains("val-svc2")


async def test_revisions_current_only_filter(client):
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env = await create_environment(client)

    await create_revision(client, sv["id"], [svc["id"], env["id"]], "v1")
    await create_revision(client, sv["id"], [svc["id"], env["id"]], "v2")

    # All revisions
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]]})
    all_revs = body["data"]["sharedValuesByIds"][0]["revisions"]["edges"]
    assert_that(all_revs).described_as("all revisions count").is_length(2)

    # Current only
    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]], "currentOnly": True}
    )
    current_revs = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
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
        await create_revision(client, sv["id"], [svc["id"], env["id"]], f"v{i}")

    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]], "first": 2})
    page1 = body["data"]["sharedValuesByIds"][0]["revisions"]
    assert_that(page1["edges"]).described_as("revision page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as(
        "revision page 1 has next page"
    ).is_true()

    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS,
        {"ids": [sv["id"]], "first": 2, "after": page1["pageInfo"]["endCursor"]},
    )
    page2 = body["data"]["sharedValuesByIds"][0]["revisions"]
    assert_that(page2["edges"]).described_as("revision page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as(
        "revision page 2 has next page"
    ).is_true()

    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS,
        {"ids": [sv["id"]], "first": 2, "after": page2["pageInfo"]["endCursor"]},
    )
    page3 = body["data"]["sharedValuesByIds"][0]["revisions"]
    assert_that(page3["edges"]).described_as("revision page 3 edge count").is_length(1)
    assert_that(page3["pageInfo"]["hasNextPage"]).described_as(
        "revision page 3 has no next page"
    ).is_false()


async def test_revisions_filter_by_environment(client):
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env1 = await create_environment(client, "production")
    env2 = await create_environment(client, "staging")

    await create_revision(client, sv["id"], [svc["id"], env1["id"]], "prod-val")
    await create_revision(client, sv["id"], [svc["id"], env2["id"]], "staging-val")

    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS,
        {"ids": [sv["id"]], "dimensionIds": [env1["id"]]},
    )
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    assert_that(revisions).described_as(
        "revisions filtered by production env"
    ).is_length(1)
    assert_that(revisions).extracting("value").described_as(
        "production revision value"
    ).contains("prod-val")


async def test_create_shared_value_with_percent_in_name_fails(client):
    body = await gql(
        client, CREATE_SHARED_VALUE, {"input": {"name": "bad%name"}}, expect_errors=True
    )
    assert_that(body).described_as("percent in name rejected").contains_key("errors")


async def test_create_shared_value_with_backslash_in_name_fails(client):
    body = await gql(
        client,
        CREATE_SHARED_VALUE,
        {"input": {"name": "bad\\name"}},
        expect_errors=True,
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
    assert_that(body).described_as("percent in update name rejected").contains_key(
        "errors"
    )


async def test_shared_value_name_with_underscore_allowed(client):
    sv = await create_shared_value(client, "my_value")
    assert_that(sv["name"]).described_as("underscore in name").is_equal_to("my_value")


# -- Nested relationship / loader tests --


REVISION_WITH_TYPED_DIMENSIONS = """
query SharedValueWithRevisions($ids: [ID!]!) {
    sharedValuesByIds(ids: $ids) {
        id name
        revisions {
            edges {
                node {
                    id value isCurrent
                    sharedValue { id name }
                    dimensions { id name type { id name } }
                }
            }
        }
    }
}
"""


async def test_revision_dimensions_include_type(client):
    """Revision.dimensions should resolve nested type via DimensionTypeLoader."""
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env = await create_environment(client)
    await create_revision(client, sv["id"], [svc["id"], env["id"]], "val")

    body = await gql(client, REVISION_WITH_TYPED_DIMENSIONS, {"ids": [sv["id"]]})
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    assert_that(revisions).is_length(1)
    for dim in revisions[0]["dimensions"]:
        assert_that(dim["type"]).described_as("dimension has type").contains_key(
            "id", "name"
        )
        assert_that(dim["type"]["name"]).described_as("type name").is_in(
            "service", "environment"
        )


async def test_revision_shared_value_resolved(client):
    """Revision.sharedValue should resolve via SharedValueLoader."""
    sv = await create_shared_value(client, "my_secret")
    svc = await create_service(client)
    env = await create_environment(client)
    await create_revision(client, sv["id"], [svc["id"], env["id"]], "val")

    body = await gql(client, REVISION_WITH_TYPED_DIMENSIONS, {"ids": [sv["id"]]})
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    assert_that(revisions[0]["sharedValue"]["id"]).described_as(
        "revision -> sv id"
    ).is_equal_to(sv["id"])
    assert_that(revisions[0]["sharedValue"]["name"]).described_as(
        "revision -> sv name"
    ).is_equal_to("my_secret")


# -- Base dimension auto-population tests --


async def test_create_revision_empty_dimensions_assigns_base(client):
    """Creating a revision with no dimensions should auto-assign all base dimensions."""
    sv = await create_shared_value(client)
    rev = await create_revision(client, sv["id"], [], "base-val")

    assert_that(rev["value"]).described_as("revision value").is_equal_to("base-val")
    assert_that(rev["isCurrent"]).described_as("revision is current").is_true()
    dim_names = [d["name"] for d in rev["dimensions"]]
    assert_that(dim_names).described_as(
        "empty dimensionIds should resolve to base dimensions"
    ).contains("global")
    assert_that(rev["dimensions"]).described_as(
        "should have one base dimension per type"
    ).is_length(2)


async def test_base_revision_appears_in_unfiltered_list(client):
    """A revision with empty dimensions should appear when listing all revisions."""
    sv = await create_shared_value(client)
    rev = await create_revision(client, sv["id"], [], "base-val")

    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]]})
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    assert_that(revisions).described_as("unfiltered revisions include base").is_length(
        1
    )
    assert_that(revisions[0]["id"]).described_as("revision id matches").is_equal_to(
        rev["id"]
    )


async def test_base_revision_appears_with_include_base(client):
    """Filtering by dimension with includeBase=true should include base revision."""
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env = await create_environment(client)

    await create_revision(client, sv["id"], [], "base-val")
    await create_revision(client, sv["id"], [svc["id"], env["id"]], "specific-val")

    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS_INCLUDE_BASE,
        {"ids": [sv["id"]], "dimensionIds": [svc["id"]], "includeBase": True},
    )
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    values = [r["value"] for r in revisions]
    assert_that(values).described_as(
        "includeBase=true should return both base and specific revisions"
    ).contains("base-val", "specific-val")


async def test_base_revision_excluded_without_include_base(client):
    """Filtering by dimension with includeBase=false should exclude base revision."""
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env = await create_environment(client)

    await create_revision(client, sv["id"], [], "base-val")
    await create_revision(client, sv["id"], [svc["id"], env["id"]], "specific-val")

    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS_INCLUDE_BASE,
        {"ids": [sv["id"]], "dimensionIds": [svc["id"]], "includeBase": False},
    )
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    values = [r["value"] for r in revisions]
    assert_that(values).described_as(
        "includeBase=false should exclude base revision"
    ).contains("specific-val").does_not_contain("base-val")


async def test_new_base_revision_replaces_current_base(client):
    """Second revision with empty dims should replace the first as current."""
    sv = await create_shared_value(client)
    rev1 = await create_revision(client, sv["id"], [], "base-v1")
    rev2 = await create_revision(client, sv["id"], [], "base-v2")

    assert_that(rev2["isCurrent"]).described_as(
        "new base revision is current"
    ).is_true()

    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]]})
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    by_id = {r["id"]: r for r in revisions}
    assert_that(by_id[rev1["id"]]["isCurrent"]).described_as(
        "old base revision no longer current"
    ).is_false()
    assert_that(by_id[rev2["id"]]["isCurrent"]).described_as(
        "new base revision is current"
    ).is_true()


async def test_new_dimension_type_backfills_base_into_revisions(client):
    """Adding a dimension type should backfill base dim into revisions.

    The old base revision gets the new global dimension added to its
    scope and its scope_hash is recomputed, so a new empty-dimensions
    revision replaces it rather than creating a separate scope.
    """
    sv = await create_shared_value(client)
    rev_before = await create_revision(client, sv["id"], [], "before-new-type")

    # Add a new dimension type — should backfill base dim into existing revision
    await create_dimension_type(client, "region")

    # Old revision should now have 3 dimensions (all globals)
    body = await gql(client, REVISION_WITH_TYPED_DIMENSIONS, {"ids": [sv["id"]]})
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    assert_that(revisions).described_as("revision still visible").is_length(1)
    assert_that(revisions[0]["id"]).is_equal_to(rev_before["id"])
    type_names = sorted(d["type"]["name"] for d in revisions[0]["dimensions"])
    assert_that(type_names).described_as(
        "old revision now includes all base dimensions"
    ).is_equal_to(["environment", "region", "service"])

    # A new empty-dimensions revision should replace the old one as current (same scope)
    rev_after = await create_revision(client, sv["id"], [], "after-new-type")
    assert_that(rev_after["isCurrent"]).described_as(
        "new revision is current"
    ).is_true()

    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]]})
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    by_id = {r["id"]: r for r in revisions}
    assert_that(by_id[rev_before["id"]]["isCurrent"]).described_as(
        "old base revision replaced as current"
    ).is_false()
    assert_that(by_id[rev_after["id"]]["isCurrent"]).described_as(
        "new base revision is current"
    ).is_true()


async def test_new_dimension_type_backfills_scoped_revisions(client):
    """Adding a new dimension type should also backfill into non-base revisions."""
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env = await create_environment(client)
    await create_revision(client, sv["id"], [svc["id"], env["id"]], "scoped-val")

    await create_dimension_type(client, "region")

    body = await gql(client, REVISION_WITH_TYPED_DIMENSIONS, {"ids": [sv["id"]]})
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    assert_that(revisions).is_length(1)
    type_names = sorted(d["type"]["name"] for d in revisions[0]["dimensions"])
    assert_that(type_names).described_as(
        "scoped revision gets new base dimension added"
    ).is_equal_to(["environment", "region", "service"])


async def test_partial_dimensions_fills_missing_with_global(client):
    """Specifying only some dimensions should fill the rest with globals."""
    sv = await create_shared_value(client)
    svc = await create_service(client)

    rev = await create_revision(client, sv["id"], [svc["id"]], "svc-only")
    dim_names = {d["name"] for d in rev["dimensions"]}
    assert_that(dim_names).described_as(
        "should include specified service and global environment"
    ).contains(svc["name"], "global")
    assert_that(rev["dimensions"]).described_as(
        "one per dimension type"
    ).is_length(2)


async def test_partial_dimensions_env_only(client):
    """Specifying only environment should fill service with global."""
    sv = await create_shared_value(client)
    env = await create_environment(client)

    await create_revision(client, sv["id"], [env["id"]], "env-only")

    body = await gql(
        client, REVISION_WITH_TYPED_DIMENSIONS, {"ids": [sv["id"]]}
    )
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    dims = revisions[0]["dimensions"]
    by_type = {d["type"]["name"]: d["name"] for d in dims}
    assert_that(by_type).described_as("types covered").contains_key(
        "service", "environment"
    )
    assert_that(by_type["service"]).described_as(
        "service auto-filled with global"
    ).is_equal_to("global")
    assert_that(by_type["environment"]).described_as(
        "environment is the one we specified"
    ).is_equal_to(env["name"])


# -- Set/Unset revision current tests --

SET_REVISION_CURRENT = """
mutation SetRevisionCurrent($id: ID!, $isCurrent: Boolean!) {
    setRevisionCurrent(id: $id, isCurrent: $isCurrent) {
        id value isCurrent
    }
}
"""


async def test_set_noncurrent_revision_to_current(client):
    """Making a non-current revision current should unset the old current."""
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env = await create_environment(client)

    rev1 = await create_revision(client, sv["id"], [svc["id"], env["id"]], "v1")
    rev2 = await create_revision(client, sv["id"], [svc["id"], env["id"]], "v2")

    # rev1 is not current, rev2 is current — make rev1 current again
    body = await gql(client, SET_REVISION_CURRENT, {"id": rev1["id"], "isCurrent": True})
    result = body["data"]["setRevisionCurrent"]
    assert_that(result["id"]).is_equal_to(rev1["id"])
    assert_that(result["isCurrent"]).described_as("rev1 now current").is_true()

    # Verify rev2 is no longer current
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]]})
    by_id = {e["node"]["id"]: e["node"] for e in body["data"]["sharedValuesByIds"][0]["revisions"]["edges"]}
    assert_that(by_id[rev1["id"]]["isCurrent"]).described_as("rev1 is current").is_true()
    assert_that(by_id[rev2["id"]]["isCurrent"]).described_as("rev2 no longer current").is_false()


async def test_deactivate_current_revision(client):
    """Unsetting current should leave no current revision for that scope."""
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env = await create_environment(client)

    rev = await create_revision(client, sv["id"], [svc["id"], env["id"]], "v1")

    body = await gql(client, SET_REVISION_CURRENT, {"id": rev["id"], "isCurrent": False})
    result = body["data"]["setRevisionCurrent"]
    assert_that(result["isCurrent"]).described_as("revision deactivated").is_false()

    # currentOnly should return nothing
    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]], "currentOnly": True}
    )
    current_revs = body["data"]["sharedValuesByIds"][0]["revisions"]["edges"]
    assert_that(current_revs).described_as("no current revisions").is_empty()


async def test_set_current_only_affects_same_scope(client):
    """Setting current should only unset revisions with the same scope."""
    sv = await create_shared_value(client)
    svc = await create_service(client)
    env1 = await create_environment(client, "production")
    env2 = await create_environment(client, "staging")

    rev_prod = await create_revision(client, sv["id"], [svc["id"], env1["id"]], "prod")
    rev_staging = await create_revision(client, sv["id"], [svc["id"], env2["id"]], "staging")

    # Both should be current (different scopes)
    assert_that(rev_prod["isCurrent"]).is_true()
    assert_that(rev_staging["isCurrent"]).is_true()

    # Add a second prod revision, then re-activate the first
    rev_prod2 = await create_revision(client, sv["id"], [svc["id"], env1["id"]], "prod2")
    await gql(client, SET_REVISION_CURRENT, {"id": rev_prod["id"], "isCurrent": True})

    # Staging should still be current
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]]})
    by_id = {e["node"]["id"]: e["node"] for e in body["data"]["sharedValuesByIds"][0]["revisions"]["edges"]}
    assert_that(by_id[rev_staging["id"]]["isCurrent"]).described_as(
        "staging unaffected"
    ).is_true()
    assert_that(by_id[rev_prod["id"]]["isCurrent"]).described_as(
        "old prod now current"
    ).is_true()
    assert_that(by_id[rev_prod2["id"]]["isCurrent"]).described_as(
        "new prod no longer current"
    ).is_false()


async def test_set_current_not_found(client):
    """Setting current on a non-existent revision should error."""
    body = await gql(
        client,
        SET_REVISION_CURRENT,
        {"id": "00000000-0000-0000-0000-ffffffffffff", "isCurrent": True},
        expect_errors=True,
    )
    assert_that(body).described_as("not found error").contains_key("errors")


# -- resolve_for_scope data layer tests --


async def test_resolve_for_scope_exact_match(client, pool):
    """resolve_for_scope returns the current revision for an exact scope match."""
    from lanterna_magica.data.shared_values import SharedValues

    sv = await create_shared_value(client, "resolve_exact")
    svc = await create_service(client, "myapp")
    env = await create_environment(client, "staging")

    rev = await create_revision(client, sv["id"], [svc["id"], env["id"]], "scoped-val")

    shared_values = SharedValues(pool)
    result = await shared_values.resolve_for_scope(
        shared_value_id=sv["id"],
        dimension_ids=[svc["id"], env["id"]],
    )

    assert_that(result).described_as("result should not be None").is_not_none()
    assert_that(str(result["id"])).described_as("matched revision id").is_equal_to(
        rev["id"]
    )
    assert_that(result["value"]).described_as("matched revision value").is_equal_to(
        "scoped-val"
    )
    assert_that(result["is_current"]).described_as("revision is current").is_true()


async def test_resolve_for_scope_priority_tiebreaking(client, pool):
    """When multiple revisions match the scope, the one with lower type priority wins.

    dimension_type priorities: service=1 (higher importance), environment=2
    A revision scoped to service=foo should win over one scoped to env=prod
    when the config is scoped to [service=foo, env=prod].
    """
    from lanterna_magica.data.shared_values import SharedValues

    sv = await create_shared_value(client, "resolve_priority")
    svc = await create_service(client, "priority-svc")
    env = await create_environment(client, "priority-env")

    # Create revision scoped to service only (global env auto-filled)
    rev_svc = await create_revision(client, sv["id"], [svc["id"]], "service-val")
    # Create revision scoped to env only (global svc auto-filled)
    await create_revision(client, sv["id"], [env["id"]], "env-val")

    shared_values = SharedValues(pool)
    result = await shared_values.resolve_for_scope(
        shared_value_id=sv["id"],
        dimension_ids=[svc["id"], env["id"]],
    )

    assert_that(result).described_as("result should not be None").is_not_none()
    assert_that(result["value"]).described_as(
        "service revision wins due to lower priority number"
    ).is_equal_to("service-val")
    assert_that(str(result["id"])).described_as(
        "service-scoped revision id returned"
    ).is_equal_to(rev_svc["id"])


async def test_resolve_for_scope_global_fallback(client, pool):
    """When no specific revision matches, the global (base-only) revision is returned."""
    from lanterna_magica.data.shared_values import SharedValues

    sv = await create_shared_value(client, "resolve_global")
    svc = await create_service(client, "other-svc")
    env = await create_environment(client, "other-env")

    # Create only a global (base-only) revision
    rev_global = await create_revision(client, sv["id"], [], "global-val")

    shared_values = SharedValues(pool)
    result = await shared_values.resolve_for_scope(
        shared_value_id=sv["id"],
        dimension_ids=[svc["id"], env["id"]],
    )

    assert_that(result).described_as("global fallback should be returned").is_not_none()
    assert_that(result["value"]).described_as("global revision value").is_equal_to(
        "global-val"
    )
    assert_that(str(result["id"])).described_as(
        "global revision id returned"
    ).is_equal_to(rev_global["id"])


async def test_resolve_for_scope_no_match_returns_none(client, pool):
    """Returns None when no current revision exists at all for the shared value."""
    from lanterna_magica.data.shared_values import SharedValues

    sv = await create_shared_value(client, "resolve_none")
    svc = await create_service(client, "unmatched-svc")
    env = await create_environment(client, "unmatched-env")

    shared_values = SharedValues(pool)
    result = await shared_values.resolve_for_scope(
        shared_value_id=sv["id"],
        dimension_ids=[svc["id"], env["id"]],
    )

    assert_that(result).described_as(
        "no revision should return None"
    ).is_none()


async def test_resolve_for_scope_out_of_scope_revision_excluded(client, pool):
    """A revision scoped to a dimension not in the config's scope is excluded."""
    from lanterna_magica.data.shared_values import SharedValues

    sv = await create_shared_value(client, "resolve_exclusion")
    svc1 = await create_service(client, "svc-alpha")
    svc2 = await create_service(client, "svc-beta")
    env = await create_environment(client, "excl-env")

    # Revision for svc2 only — should NOT match a config scoped to [svc1, env]
    await create_revision(client, sv["id"], [svc2["id"]], "svc2-val")

    shared_values = SharedValues(pool)
    result = await shared_values.resolve_for_scope(
        shared_value_id=sv["id"],
        dimension_ids=[svc1["id"], env["id"]],
    )

    assert_that(result).described_as(
        "out-of-scope revision should not match"
    ).is_none()


async def test_resolve_for_scope_specificity_tiebreaker(client, pool):
    """More specific revisions (more non-base dimensions) win over less specific ones
    when both match the scope and have the same minimum dimension type priority.

    Revision A: scoped to [service=X] (one non-base dimension, global env auto-filled)
    Revision B: scoped to [service=X, env=Y] (two non-base dimensions)
    Both match dimension_ids=[svc_x, env_y]. Revision B must win via COUNT(*) DESC.
    """
    from lanterna_magica.data.shared_values import SharedValues

    sv = await create_shared_value(client, "resolve_specificity")
    svc = await create_service(client, "spec-svc")
    env = await create_environment(client, "spec-env")

    # Less specific: scoped to service only (global env auto-filled)
    await create_revision(client, sv["id"], [svc["id"]], "svc-only-val")
    # More specific: scoped to service AND env
    rev_specific = await create_revision(
        client, sv["id"], [svc["id"], env["id"]], "svc-and-env-val"
    )

    shared_values = SharedValues(pool)
    result = await shared_values.resolve_for_scope(
        shared_value_id=sv["id"],
        dimension_ids=[svc["id"], env["id"]],
    )

    assert_that(result).described_as("result should not be None").is_not_none()
    assert_that(result["value"]).described_as(
        "more specific revision wins over less specific"
    ).is_equal_to("svc-and-env-val")
    assert_that(str(result["id"])).described_as(
        "specific revision id returned"
    ).is_equal_to(rev_specific["id"])


# -- Data-layer tests for SharedValues.get_by_ids --


async def test_get_by_ids_multiple(client, pool):
    """get_by_ids returns multiple shared values by their IDs."""
    from lanterna_magica.data.shared_values import SharedValues

    sv_a = await create_shared_value(client, "sv_alpha")
    sv_b = await create_shared_value(client, "sv_beta")
    sv_c = await create_shared_value(client, "sv_gamma")

    shared_values = SharedValues(pool)
    result = await shared_values.get_by_ids(ids=[sv_a["id"], sv_c["id"]])

    assert_that(result).described_as("returns two shared values").is_length(2)
    returned_ids = {str(r["id"]) for r in result}
    assert_that(returned_ids).described_as("correct ids returned").is_equal_to(
        {sv_a["id"], sv_c["id"]}
    )
    assert_that(sv_b["id"]).described_as("unrequested sv absent").is_not_in(returned_ids)


async def test_get_by_ids_empty_list(pool):
    """get_by_ids returns an empty list when given no IDs."""
    from lanterna_magica.data.shared_values import SharedValues

    shared_values = SharedValues(pool)
    result = await shared_values.get_by_ids(ids=[])
    assert_that(result).described_as("empty list for empty ids").is_equal_to([])


async def test_get_by_ids_unknown_ids(pool):
    """get_by_ids returns an empty list when no IDs match."""
    from lanterna_magica.data.shared_values import SharedValues

    shared_values = SharedValues(pool)
    result = await shared_values.get_by_ids(ids=["00000000-0000-0000-0000-ffffffffffff"])
    assert_that(result).described_as("empty list for unknown ids").is_equal_to([])

# -- resolveSharedValue query tests --

RESOLVE_SHARED_VALUE = """
query ResolveSharedValue($sharedValueId: ID!, $dimensionIds: [ID!]!) {
    resolveSharedValue(sharedValueId: $sharedValueId, dimensionIds: $dimensionIds) {
        id sharedValue { id } dimensions { id name } value isCurrent createdAt
    }
}
"""


async def test_resolve_shared_value_match(client):
    """resolveSharedValue returns the best-matching current revision."""
    sv = await create_shared_value(client, "gql_resolve_match")
    svc = await create_service(client, "gql-svc")
    env = await create_environment(client, "gql-env")

    rev = await create_revision(client, sv["id"], [svc["id"], env["id"]], "gql-secret")

    body = await gql(
        client,
        RESOLVE_SHARED_VALUE,
        {"sharedValueId": sv["id"], "dimensionIds": [svc["id"], env["id"]]},
    )
    result = body["data"]["resolveSharedValue"]

    assert_that(result).described_as("result should not be null").is_not_none()
    assert_that(result["id"]).described_as("returned revision id").is_equal_to(rev["id"])
    assert_that(result["value"]).described_as("returned revision value").is_equal_to("gql-secret")
    assert_that(result["sharedValue"]["id"]).described_as(
        "revision belongs to correct shared value"
    ).is_equal_to(sv["id"])
    assert_that(result["isCurrent"]).described_as("revision is current").is_true()


async def test_resolve_shared_value_no_match(client):
    """resolveSharedValue returns null when no revision covers the given scope."""
    sv = await create_shared_value(client, "gql_resolve_no_match")
    svc1 = await create_service(client, "gql-svc-nomatch-1")
    svc2 = await create_service(client, "gql-svc-nomatch-2")
    env = await create_environment(client, "gql-env-nomatch")

    # Create a revision scoped to svc2 — should NOT match a query for svc1
    await create_revision(client, sv["id"], [svc2["id"], env["id"]], "wrong-svc-val")

    body = await gql(
        client,
        RESOLVE_SHARED_VALUE,
        {"sharedValueId": sv["id"], "dimensionIds": [svc1["id"], env["id"]]},
    )
    result = body["data"]["resolveSharedValue"]

    assert_that(result).described_as(
        "no matching revision should return null"
    ).is_none()


# -- Type uniqueness validation tests --

CREATE_SHARED_VALUE_REVISION = """
mutation CreateSharedValueRevision($input: CreateSharedValueRevisionInput!) {
    createSharedValueRevision(input: $input) {
        id value isCurrent
        dimensions { id name }
    }
}
"""


async def test_create_revision_duplicate_dimension_type_raises_error(client):
    """Creating a revision with two dimensions of the same type should fail."""
    sv = await create_shared_value(client, "dup_type_sv")
    svc1 = await create_service(client, "rev-svc-alpha")
    svc2 = await create_service(client, "rev-svc-beta")

    body = await gql(
        client,
        CREATE_SHARED_VALUE_REVISION,
        {
            "input": {
                "sharedValueId": sv["id"],
                "dimensionIds": [svc1["id"], svc2["id"]],
                "value": "test",
            }
        },
        expect_errors=True,
    )
    assert_that(body).described_as("duplicate type error response").contains_key("errors")
    error_message = body["errors"][0]["message"]
    assert_that(error_message).described_as(
        "error mentions duplicate type"
    ).contains("multiple dimensions of the same type")


# -- DataLoader: SharedValue.usedBy --

_CREATE_CONFIGURATION_FOR_LOADER = """
mutation CreateConfigurationForLoader($input: CreateConfigurationInput!) {
    createConfiguration(input: $input) {
        id body isCurrent
        substitutions { id jsonpath sharedValue { id } }
    }
}
"""

_SHARED_VALUES_BY_IDS_WITH_USED_BY = """
query SharedValuesByIdsWithUsedBy($ids: [ID!]!) {
    sharedValuesByIds(ids: $ids) {
        id name
        usedBy {
            edges {
                node { id isCurrent }
            }
            pageInfo { hasNextPage endCursor }
        }
    }
}
"""


async def _create_configuration_with_substitution(client, dimension_ids, body_json, substitutions):
    variables = {
        "input": {
            "dimensionIds": dimension_ids,
            "body": body_json,
            "substitutions": substitutions,
        }
    }
    result = await gql(client, _CREATE_CONFIGURATION_FOR_LOADER, variables)
    return result["data"]["createConfiguration"]


async def test_used_by_dataloader_single_shared_value(client):
    """usedBy via DataLoader returns configurations referencing the shared value."""
    svc = await create_service(client, "loader-svc-single")
    env = await create_environment(client, "loader-env-single")
    sv = await create_shared_value(client, "loader_single_secret")

    cfg = await _create_configuration_with_substitution(
        client,
        [svc["id"], env["id"]],
        {"key": "_"},
        [{"jsonpath": "$.key", "sharedValueId": sv["id"]}],
    )

    body = await gql(client, _SHARED_VALUES_BY_IDS_WITH_USED_BY, {"ids": [sv["id"]]})
    result = body["data"]["sharedValuesByIds"][0]
    config_ids = [e["node"]["id"] for e in result["usedBy"]["edges"]]

    assert_that(config_ids).described_as(
        "configuration referencing shared value should appear in usedBy via DataLoader"
    ).contains(cfg["id"])


async def test_used_by_dataloader_multiple_shared_values_batched(client):
    """Fetching usedBy for multiple shared values in one query uses the DataLoader."""
    svc = await create_service(client, "loader-svc-batch")
    env = await create_environment(client, "loader-env-batch")
    sv1 = await create_shared_value(client, "loader_batch_secret_1")
    sv2 = await create_shared_value(client, "loader_batch_secret_2")

    cfg1 = await _create_configuration_with_substitution(
        client,
        [svc["id"], env["id"]],
        {"key1": "_"},
        [{"jsonpath": "$.key1", "sharedValueId": sv1["id"]}],
    )
    # Create a different scope for sv2 so configs don't conflict
    env2 = await create_environment(client, "loader-env-batch-2")
    cfg2 = await _create_configuration_with_substitution(
        client,
        [svc["id"], env2["id"]],
        {"key2": "_"},
        [{"jsonpath": "$.key2", "sharedValueId": sv2["id"]}],
    )

    body = await gql(
        client,
        _SHARED_VALUES_BY_IDS_WITH_USED_BY,
        {"ids": [sv1["id"], sv2["id"]]},
    )
    results = {r["id"]: r for r in body["data"]["sharedValuesByIds"]}

    ids_for_sv1 = [e["node"]["id"] for e in results[sv1["id"]]["usedBy"]["edges"]]
    ids_for_sv2 = [e["node"]["id"] for e in results[sv2["id"]]["usedBy"]["edges"]]

    assert_that(ids_for_sv1).described_as(
        "cfg1 should appear in sv1.usedBy"
    ).contains(cfg1["id"])
    assert_that(ids_for_sv2).described_as(
        "cfg2 should appear in sv2.usedBy"
    ).contains(cfg2["id"])
    assert_that(ids_for_sv1).described_as(
        "cfg2 should not appear in sv1.usedBy"
    ).does_not_contain(cfg2["id"])
    assert_that(ids_for_sv2).described_as(
        "cfg1 should not appear in sv2.usedBy"
    ).does_not_contain(cfg1["id"])


async def test_used_by_dataloader_excludes_archived_by_default(client, pool):
    """usedBy via DataLoader (default path) excludes archived configurations."""
    svc = await create_service(client, "loader-svc-archived")
    env = await create_environment(client, "loader-env-archived")
    sv = await create_shared_value(client, "loader_archived_secret")

    cfg = await _create_configuration_with_substitution(
        client,
        [svc["id"], env["id"]],
        {"secret": "_"},
        [{"jsonpath": "$.secret", "sharedValueId": sv["id"]}],
    )

    # Archive the configuration directly via DB
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE configurations SET archived_at = now() WHERE id = $1",
            cfg["id"],
        )

    body = await gql(client, _SHARED_VALUES_BY_IDS_WITH_USED_BY, {"ids": [sv["id"]]})
    result = body["data"]["sharedValuesByIds"][0]
    config_ids = [e["node"]["id"] for e in result["usedBy"]["edges"]]

    assert_that(config_ids).described_as(
        "archived config should not appear in usedBy via DataLoader default path"
    ).does_not_contain(cfg["id"])


async def test_used_by_dataloader_empty_for_unreferenced_shared_value(client):
    """usedBy returns empty connection for a shared value with no configurations."""
    sv = await create_shared_value(client, "loader_unreferenced")

    body = await gql(client, _SHARED_VALUES_BY_IDS_WITH_USED_BY, {"ids": [sv["id"]]})
    result = body["data"]["sharedValuesByIds"][0]

    assert_that(result["usedBy"]["edges"]).described_as(
        "unreferenced shared value should have empty usedBy"
    ).is_empty()
    assert_that(result["usedBy"]["pageInfo"]["hasNextPage"]).described_as(
        "hasNextPage should be false for empty usedBy"
    ).is_false()


async def test_used_by_dataloader_deduplicates_multiple_substitutions(client):
    """A configuration with two substitutions referencing the same shared value at different
    JSONPaths should appear exactly once in usedBy, not once per substitution."""
    svc = await create_service(client, "loader-svc-dedup")
    env = await create_environment(client, "loader-env-dedup")
    sv = await create_shared_value(client, "loader_dedup_secret")

    cfg = await _create_configuration_with_substitution(
        client,
        [svc["id"], env["id"]],
        {"db": {"host": "_", "replica": "_"}},
        [
            {"jsonpath": "$.db.host", "sharedValueId": sv["id"]},
            {"jsonpath": "$.db.replica", "sharedValueId": sv["id"]},
        ],
    )

    body = await gql(client, _SHARED_VALUES_BY_IDS_WITH_USED_BY, {"ids": [sv["id"]]})
    result = body["data"]["sharedValuesByIds"][0]
    config_ids = [e["node"]["id"] for e in result["usedBy"]["edges"]]

    assert_that(config_ids).described_as(
        "configuration should appear in usedBy"
    ).contains(cfg["id"])
    assert_that(config_ids.count(cfg["id"])).described_as(
        "configuration with two substitutions to same shared value should appear exactly once"
    ).is_equal_to(1)
