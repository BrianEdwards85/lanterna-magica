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
    $dimensionIds: [ID!],
    $currentOnly: Boolean,
    $first: Int,
    $after: String
) {
    sharedValue(id: $id) {
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
    $id: ID!,
    $dimensionIds: [ID!],
    $includeBase: Boolean,
    $currentOnly: Boolean,
    $first: Int,
    $after: String
) {
    sharedValue(id: $id) {
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


async def test_shared_value_by_id(client):
    sv = await create_shared_value(client)
    body = await gql(client, SHARED_VALUE, {"id": sv["id"]})
    found = body["data"]["sharedValue"]
    assert_that(found["id"]).described_as("fetched shared value id").is_equal_to(
        sv["id"]
    )
    assert_that(found["name"]).described_as("fetched shared value name").is_equal_to(
        sv["name"]
    )


async def test_shared_value_by_id_not_found(client):
    body = await gql(
        client, SHARED_VALUE, {"id": "00000000-0000-0000-0000-ffffffffffff"}
    )
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
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"]})
    revisions = body["data"]["sharedValue"]["revisions"]["edges"]
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
        {"id": sv["id"], "dimensionIds": [svc1["id"]]},
    )
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
    assert_that(revisions).described_as("revisions filtered by svc1").is_length(1)
    assert_that(revisions).extracting("value").described_as(
        "svc1 revision value"
    ).contains("val-svc1")

    # Filter by svc2
    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS,
        {"id": sv["id"], "dimensionIds": [svc2["id"]]},
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

    await create_revision(client, sv["id"], [svc["id"], env["id"]], "v1")
    await create_revision(client, sv["id"], [svc["id"], env["id"]], "v2")

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
        await create_revision(client, sv["id"], [svc["id"], env["id"]], f"v{i}")

    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "first": 2})
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

    await create_revision(client, sv["id"], [svc["id"], env1["id"]], "prod-val")
    await create_revision(client, sv["id"], [svc["id"], env2["id"]], "staging-val")

    body = await gql(
        client,
        SHARED_VALUE_WITH_REVISIONS,
        {"id": sv["id"], "dimensionIds": [env1["id"]]},
    )
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
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
query SharedValueWithRevisions($id: ID!) {
    sharedValue(id: $id) {
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

    body = await gql(client, REVISION_WITH_TYPED_DIMENSIONS, {"id": sv["id"]})
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
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

    body = await gql(client, REVISION_WITH_TYPED_DIMENSIONS, {"id": sv["id"]})
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
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

    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"]})
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
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
        {"id": sv["id"], "dimensionIds": [svc["id"]], "includeBase": True},
    )
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
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
        {"id": sv["id"], "dimensionIds": [svc["id"]], "includeBase": False},
    )
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
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

    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"]})
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
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
    body = await gql(client, REVISION_WITH_TYPED_DIMENSIONS, {"id": sv["id"]})
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
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

    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"]})
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
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

    body = await gql(client, REVISION_WITH_TYPED_DIMENSIONS, {"id": sv["id"]})
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
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
        client, REVISION_WITH_TYPED_DIMENSIONS, {"id": sv["id"]}
    )
    revisions = nodes(body["data"]["sharedValue"]["revisions"]["edges"])
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
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"]})
    by_id = {e["node"]["id"]: e["node"] for e in body["data"]["sharedValue"]["revisions"]["edges"]}
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
        client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"], "currentOnly": True}
    )
    current_revs = body["data"]["sharedValue"]["revisions"]["edges"]
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
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"id": sv["id"]})
    by_id = {e["node"]["id"]: e["node"] for e in body["data"]["sharedValue"]["revisions"]["edges"]}
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
