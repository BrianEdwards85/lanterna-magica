from assertpy import assert_that
from conftest import gql
from gql import (
    REVISION_WITH_TYPED_DIMENSIONS,
    SHARED_VALUE_WITH_REVISIONS,
    SHARED_VALUE_WITH_REVISIONS_INCLUDE_BASE,
    create_dimension_type,
    create_environment,
    create_revision,
    create_service,
    create_shared_value,
)
from utils import nodes

from lanterna_magica.data.shared_values import SharedValues

# -- Base dimension auto-population tests --


async def test_create_revision_empty_dimensions_assigns_base(client):
    """Creating a revision with no dimensions should auto-assign all base dimensions."""
    sv = await create_shared_value(client)
    rev = await create_revision(client, sv["id"], [], "base-val")

    assert_that(rev["value"]).described_as("revision value").is_equal_to("base-val")
    assert_that(rev["isCurrent"]).described_as("revision is current").is_true()
    dim_names = [d["name"] for d in rev["dimensions"]]
    assert_that(dim_names).described_as("empty dimensionIds should resolve to base dimensions").contains("global")
    assert_that(rev["dimensions"]).described_as("should have one base dimension per type").is_length(2)


async def test_base_revision_appears_in_unfiltered_list(client):
    """A revision with empty dimensions should appear when listing all revisions."""
    sv = await create_shared_value(client)
    rev = await create_revision(client, sv["id"], [], "base-val")

    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]]})
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    assert_that(revisions).described_as("unfiltered revisions include base").is_length(1)
    assert_that(revisions[0]["id"]).described_as("revision id matches").is_equal_to(rev["id"])


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
    assert_that(values).described_as("includeBase=true should return both base and specific revisions").contains(
        "base-val", "specific-val"
    )


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
    assert_that(values).described_as("includeBase=false should exclude base revision").contains(
        "specific-val"
    ).does_not_contain("base-val")


async def test_new_base_revision_replaces_current_base(client):
    """Second revision with empty dims should replace the first as current."""
    sv = await create_shared_value(client)
    rev1 = await create_revision(client, sv["id"], [], "base-v1")
    rev2 = await create_revision(client, sv["id"], [], "base-v2")

    assert_that(rev2["isCurrent"]).described_as("new base revision is current").is_true()

    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]]})
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    by_id = {r["id"]: r for r in revisions}
    assert_that(by_id[rev1["id"]]["isCurrent"]).described_as("old base revision no longer current").is_false()
    assert_that(by_id[rev2["id"]]["isCurrent"]).described_as("new base revision is current").is_true()


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
    assert_that(type_names).described_as("old revision now includes all base dimensions").is_equal_to(
        ["environment", "region", "service"]
    )

    # A new empty-dimensions revision should replace the old one as current (same scope)
    rev_after = await create_revision(client, sv["id"], [], "after-new-type")
    assert_that(rev_after["isCurrent"]).described_as("new revision is current").is_true()

    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]]})
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    by_id = {r["id"]: r for r in revisions}
    assert_that(by_id[rev_before["id"]]["isCurrent"]).described_as("old base revision replaced as current").is_false()
    assert_that(by_id[rev_after["id"]]["isCurrent"]).described_as("new base revision is current").is_true()


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
    assert_that(type_names).described_as("scoped revision gets new base dimension added").is_equal_to(
        ["environment", "region", "service"]
    )


async def test_partial_dimensions_fills_missing_with_global(client):
    """Specifying only some dimensions should fill the rest with globals."""
    sv = await create_shared_value(client)
    svc = await create_service(client)

    rev = await create_revision(client, sv["id"], [svc["id"]], "svc-only")
    dim_names = {d["name"] for d in rev["dimensions"]}
    assert_that(dim_names).described_as("should include specified service and global environment").contains(
        svc["name"], "global"
    )
    assert_that(rev["dimensions"]).described_as("one per dimension type").is_length(2)


async def test_partial_dimensions_env_only(client):
    """Specifying only environment should fill service with global."""
    sv = await create_shared_value(client)
    env = await create_environment(client)

    await create_revision(client, sv["id"], [env["id"]], "env-only")

    body = await gql(client, REVISION_WITH_TYPED_DIMENSIONS, {"ids": [sv["id"]]})
    revisions = nodes(body["data"]["sharedValuesByIds"][0]["revisions"]["edges"])
    dims = revisions[0]["dimensions"]
    by_type = {d["type"]["name"]: d["name"] for d in dims}
    assert_that(by_type).described_as("types covered").contains_key("service", "environment")
    assert_that(by_type["service"]).described_as("service auto-filled with global").is_equal_to("global")
    assert_that(by_type["environment"]).described_as("environment is the one we specified").is_equal_to(env["name"])


# -- Data-layer tests for SharedValues.get_by_ids --


async def test_get_by_ids_multiple(client, pool):
    """get_by_ids returns multiple shared values by their IDs."""
    sv_a = await create_shared_value(client, "sv_alpha")
    sv_b = await create_shared_value(client, "sv_beta")
    sv_c = await create_shared_value(client, "sv_gamma")

    shared_values = SharedValues(pool)
    result = await shared_values.get_by_ids(ids=[sv_a["id"], sv_c["id"]])

    assert_that(result).described_as("returns two shared values").is_length(2)
    returned_ids = {str(r["id"]) for r in result}
    assert_that(returned_ids).described_as("correct ids returned").is_equal_to({sv_a["id"], sv_c["id"]})
    assert_that(sv_b["id"]).described_as("unrequested sv absent").is_not_in(returned_ids)


async def test_get_by_ids_empty_list(pool):
    """get_by_ids returns an empty list when given no IDs."""
    shared_values = SharedValues(pool)
    result = await shared_values.get_by_ids(ids=[])
    assert_that(result).described_as("empty list for empty ids").is_equal_to([])


async def test_get_by_ids_unknown_ids(pool):
    """get_by_ids returns an empty list when no IDs match."""
    shared_values = SharedValues(pool)
    result = await shared_values.get_by_ids(ids=["00000000-0000-0000-0000-ffffffffffff"])
    assert_that(result).described_as("empty list for unknown ids").is_equal_to([])
