from assertpy import assert_that
from conftest import gql
from gql import (
    CREATE_SHARED_VALUE,
    RESOLVE_SHARED_VALUE,
    SET_REVISION_CURRENT,
    create_environment,
    create_revision,
    create_service,
    create_shared_value,
)

from lanterna_magica.data.shared_values import SharedValues

# -- resolve_for_scope data layer tests --


async def test_resolve_for_scope_exact_match(client, pool):
    """resolve_for_scope returns the current revision for an exact scope match."""
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
    assert_that(str(result["id"])).described_as("matched revision id").is_equal_to(rev["id"])
    assert_that(result["value"]).described_as("matched revision value").is_equal_to("scoped-val")
    assert_that(result["is_current"]).described_as("revision is current").is_true()


async def test_resolve_for_scope_priority_tiebreaking(client, pool):
    """When multiple revisions match the scope, the one with lower type priority wins.

    dimension_type priorities: service=1 (higher importance), environment=2
    A revision scoped to service=foo should win over one scoped to env=prod
    when the config is scoped to [service=foo, env=prod].
    """
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
    assert_that(result["value"]).described_as("service revision wins due to lower priority number").is_equal_to(
        "service-val"
    )
    assert_that(str(result["id"])).described_as("service-scoped revision id returned").is_equal_to(rev_svc["id"])


async def test_resolve_for_scope_global_fallback(client, pool):
    """When no specific revision matches, the global (base-only) revision is returned."""
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
    assert_that(result["value"]).described_as("global revision value").is_equal_to("global-val")
    assert_that(str(result["id"])).described_as("global revision id returned").is_equal_to(rev_global["id"])


async def test_resolve_for_scope_no_match_returns_none(client, pool):
    """Returns None when no current revision exists at all for the shared value."""
    sv = await create_shared_value(client, "resolve_none")
    svc = await create_service(client, "unmatched-svc")
    env = await create_environment(client, "unmatched-env")

    shared_values = SharedValues(pool)
    result = await shared_values.resolve_for_scope(
        shared_value_id=sv["id"],
        dimension_ids=[svc["id"], env["id"]],
    )

    assert_that(result).described_as("no revision should return None").is_none()


async def test_resolve_for_scope_out_of_scope_revision_excluded(client, pool):
    """A revision scoped to a dimension not in the config's scope is excluded."""
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

    assert_that(result).described_as("out-of-scope revision should not match").is_none()


async def test_resolve_for_scope_specificity_tiebreaker(client, pool):
    """More specific revisions (more non-base dimensions) win over less specific ones
    when both match the scope and have the same minimum dimension type priority.

    Revision A: scoped to [service=X] (one non-base dimension, global env auto-filled)
    Revision B: scoped to [service=X, env=Y] (two non-base dimensions)
    Both match dimension_ids=[svc_x, env_y]. Revision B must win via COUNT(*) DESC.
    """
    sv = await create_shared_value(client, "resolve_specificity")
    svc = await create_service(client, "spec-svc")
    env = await create_environment(client, "spec-env")

    # Less specific: scoped to service only (global env auto-filled)
    await create_revision(client, sv["id"], [svc["id"]], "svc-only-val")
    # More specific: scoped to service AND env
    rev_specific = await create_revision(client, sv["id"], [svc["id"], env["id"]], "svc-and-env-val")

    shared_values = SharedValues(pool)
    result = await shared_values.resolve_for_scope(
        shared_value_id=sv["id"],
        dimension_ids=[svc["id"], env["id"]],
    )

    assert_that(result).described_as("result should not be None").is_not_none()
    assert_that(result["value"]).described_as("more specific revision wins over less specific").is_equal_to(
        "svc-and-env-val"
    )
    assert_that(str(result["id"])).described_as("specific revision id returned").is_equal_to(rev_specific["id"])


# -- resolveSharedValue query tests --


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
    assert_that(result["sharedValue"]["id"]).described_as("revision belongs to correct shared value").is_equal_to(
        sv["id"]
    )
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

    assert_that(result).described_as("no matching revision should return null").is_none()


async def test_create_shared_value_with_percent_in_name_fails(client):
    body = await gql(client, CREATE_SHARED_VALUE, {"input": {"name": "bad%name"}}, expect_errors=True)
    assert_that(body).described_as("percent in name rejected").contains_key("errors")


async def test_create_shared_value_with_backslash_in_name_fails(client):
    body = await gql(
        client,
        CREATE_SHARED_VALUE,
        {"input": {"name": "bad\\name"}},
        expect_errors=True,
    )
    assert_that(body).described_as("backslash in name rejected").contains_key("errors")


async def test_set_current_not_found(client):
    body = await gql(
        client,
        SET_REVISION_CURRENT,
        {"id": "00000000-0000-0000-0000-ffffffffffff", "isCurrent": True},
        expect_errors=True,
    )
    assert_that(body).described_as("not found error").contains_key("errors")
