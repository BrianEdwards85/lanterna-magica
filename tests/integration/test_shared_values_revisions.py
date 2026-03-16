from assertpy import assert_that
from conftest import gql
from gql import (
    CREATE_SHARED_VALUE_REVISION,
    REVISION_WITH_TYPED_DIMENSIONS,
    SHARED_VALUE_WITH_REVISIONS,
    create_environment,
    create_revision,
    create_service,
    create_shared_value,
)
from utils import nodes

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

    body = await gql(
        client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]], "first": 2}
    )
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


# -- Nested relationship / loader tests --


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


# -- Type uniqueness validation tests --


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
    assert_that(body).described_as("duplicate type error response").contains_key(
        "errors"
    )
    error_message = body["errors"][0]["message"]
    assert_that(error_message).described_as("error mentions duplicate type").contains(
        "multiple dimensions of the same type"
    )
