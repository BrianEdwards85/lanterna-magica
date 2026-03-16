"""Integration tests for SharedValue.usedBy field."""

from assertpy import assert_that
from conftest import gql
from utils import (
    create_environment,
    create_service,
    create_shared_value,
    nodes,
)

# -- Queries --

SHARED_VALUE_USED_BY = """
query SharedValueUsedBy($ids: [ID!]!, $includeArchived: Boolean, $first: Int, $after: String) {
    sharedValuesByIds(ids: $ids) {
        id name
        usedBy(includeArchived: $includeArchived, first: $first, after: $after) {
            edges {
                node {
                    id body isCurrent
                    substitutions { id jsonpath sharedValue { id } }
                }
                cursor
            }
            pageInfo { hasNextPage endCursor }
        }
    }
}
"""

CREATE_CONFIGURATION = """
mutation CreateConfiguration($input: CreateConfigurationInput!) {
    createConfiguration(input: $input) {
        id body isCurrent
        dimensions { id name }
        substitutions { id jsonpath sharedValue { id } }
    }
}
"""


# -- Helpers --


async def _create_configuration(client, dimension_ids, body, substitutions=None):
    variables = {
        "input": {
            "dimensionIds": dimension_ids,
            "body": body,
        }
    }
    if substitutions:
        variables["input"]["substitutions"] = substitutions
    result = await gql(client, CREATE_CONFIGURATION, variables)
    return result["data"]["createConfiguration"]


async def _archive_configuration(pool, config_id):
    """Set archived_at on a configuration directly in the DB (no mutation yet)."""
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE configurations SET archived_at = now() WHERE id = $1",
            config_id,
        )


# -- Tests --


async def test_used_by_config_with_substitution_appears(client):
    """A configuration with a substitution pointing to shared value X appears in X.usedBy."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "db_password")

    cfg = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"database": {"password": "_"}},
        [{"jsonpath": "$.database.password", "sharedValueId": sv["id"]}],
    )

    body = await gql(client, SHARED_VALUE_USED_BY, {"ids": [sv["id"]]})
    used_by = body["data"]["sharedValuesByIds"][0]["usedBy"]
    config_ids = [e["node"]["id"] for e in used_by["edges"]]

    assert_that(config_ids).described_as(
        "config with substitution to sv should appear in usedBy"
    ).contains(cfg["id"])


async def test_used_by_config_without_substitution_excluded(client):
    """A configuration with no substitution to X does not appear in X.usedBy."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "db_password")
    sv_other = await create_shared_value(client, "api_key")

    # Create a configuration that substitutes sv_other, not sv
    cfg = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"api": {"key": "_"}},
        [{"jsonpath": "$.api.key", "sharedValueId": sv_other["id"]}],
    )

    body = await gql(client, SHARED_VALUE_USED_BY, {"ids": [sv["id"]]})
    used_by = body["data"]["sharedValuesByIds"][0]["usedBy"]
    config_ids = [e["node"]["id"] for e in used_by["edges"]]

    assert_that(config_ids).described_as(
        "config without substitution to sv should not appear in usedBy"
    ).does_not_contain(cfg["id"])


async def test_used_by_cross_value_isolation(client):
    """A config referencing shared value Y does not appear in Z.usedBy."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv_y = await create_shared_value(client, "value_y")
    sv_z = await create_shared_value(client, "value_z")

    # Config references Y only
    cfg_y = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"secret": "_"},
        [{"jsonpath": "$.secret", "sharedValueId": sv_y["id"]}],
    )

    body_y = await gql(client, SHARED_VALUE_USED_BY, {"ids": [sv_y["id"]]})
    body_z = await gql(client, SHARED_VALUE_USED_BY, {"ids": [sv_z["id"]]})

    ids_for_y = [e["node"]["id"] for e in body_y["data"]["sharedValuesByIds"][0]["usedBy"]["edges"]]
    ids_for_z = [e["node"]["id"] for e in body_z["data"]["sharedValuesByIds"][0]["usedBy"]["edges"]]

    assert_that(ids_for_y).described_as(
        "config referencing Y should appear in Y.usedBy"
    ).contains(cfg_y["id"])
    assert_that(ids_for_z).described_as(
        "config referencing Y should not appear in Z.usedBy"
    ).does_not_contain(cfg_y["id"])


async def test_used_by_include_archived_false_excludes_archived(client, pool):
    """includeArchived=false (default) should exclude archived configurations."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "db_password")

    cfg = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"db": {"pass": "_"}},
        [{"jsonpath": "$.db.pass", "sharedValueId": sv["id"]}],
    )

    await _archive_configuration(pool, cfg["id"])

    # Default (includeArchived not set — defaults to false)
    body = await gql(client, SHARED_VALUE_USED_BY, {"ids": [sv["id"]]})
    config_ids = [e["node"]["id"] for e in body["data"]["sharedValuesByIds"][0]["usedBy"]["edges"]]

    assert_that(config_ids).described_as(
        "archived config should not appear in usedBy with default includeArchived"
    ).does_not_contain(cfg["id"])

    # Explicit includeArchived=false
    body = await gql(client, SHARED_VALUE_USED_BY, {"ids": [sv["id"]], "includeArchived": False})
    config_ids = [e["node"]["id"] for e in body["data"]["sharedValuesByIds"][0]["usedBy"]["edges"]]

    assert_that(config_ids).described_as(
        "archived config should not appear in usedBy with includeArchived=false"
    ).does_not_contain(cfg["id"])


async def test_used_by_include_archived_true_includes_archived(client, pool):
    """includeArchived=true should include archived configurations."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "db_password")

    cfg = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"db": {"pass": "_"}},
        [{"jsonpath": "$.db.pass", "sharedValueId": sv["id"]}],
    )

    await _archive_configuration(pool, cfg["id"])

    body = await gql(client, SHARED_VALUE_USED_BY, {"ids": [sv["id"]], "includeArchived": True})
    config_ids = [e["node"]["id"] for e in body["data"]["sharedValuesByIds"][0]["usedBy"]["edges"]]

    assert_that(config_ids).described_as(
        "archived config should appear in usedBy with includeArchived=true"
    ).contains(cfg["id"])


async def test_used_by_pagination_has_next_page(client):
    """With more configs than the page size, hasNextPage is true."""
    svc = await create_service(client)
    env_list = [await create_environment(client, f"env-{i:02d}") for i in range(3)]
    sv = await create_shared_value(client, "shared_secret")

    # Create 3 configurations each referencing sv — one per environment (different scopes)
    for env in env_list:
        await _create_configuration(
            client,
            [svc["id"], env["id"]],
            {"key": "_"},
            [{"jsonpath": "$.key", "sharedValueId": sv["id"]}],
        )

    body = await gql(client, SHARED_VALUE_USED_BY, {"ids": [sv["id"]], "first": 2})
    page1 = body["data"]["sharedValuesByIds"][0]["usedBy"]

    assert_that(page1["edges"]).described_as(
        "page 1 should have 2 edges"
    ).is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as(
        "hasNextPage should be true when more results exist"
    ).is_true()


async def test_used_by_no_duplicate_when_multiple_substitutions_point_to_same_value(client):
    """A configuration with two substitutions pointing to the same shared value should
    appear exactly once in usedBy — regression test for the DISTINCT ON fix."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "multi_sub_value")

    # Create a configuration with two substitutions both pointing to the same shared value
    # at different JSONPaths. This exercises the bug where the JOIN returned two rows.
    cfg = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"db": {"host": "_", "port": "_"}},
        [
            {"jsonpath": "$.db.host", "sharedValueId": sv["id"]},
            {"jsonpath": "$.db.port", "sharedValueId": sv["id"]},
        ],
    )

    # Force the SQL code path (not DataLoader) by passing includeArchived=True
    body = await gql(client, SHARED_VALUE_USED_BY, {"ids": [sv["id"]], "includeArchived": True})
    used_by = body["data"]["sharedValuesByIds"][0]["usedBy"]
    config_ids = [e["node"]["id"] for e in used_by["edges"]]

    assert_that(config_ids).described_as(
        "config with two substitutions to same sv should appear exactly once in usedBy"
    ).contains(cfg["id"])
    assert_that(config_ids.count(cfg["id"])).described_as(
        "config id must not be duplicated in usedBy results"
    ).is_equal_to(1)


async def test_used_by_pagination_after_cursor(client):
    """The after cursor returns the next page of results."""
    svc = await create_service(client)
    env_list = [await create_environment(client, f"env-page-{i:02d}") for i in range(3)]
    sv = await create_shared_value(client, "paginated_secret")

    for env in env_list:
        await _create_configuration(
            client,
            [svc["id"], env["id"]],
            {"k": "_"},
            [{"jsonpath": "$.k", "sharedValueId": sv["id"]}],
        )

    # Get page 1
    body = await gql(client, SHARED_VALUE_USED_BY, {"ids": [sv["id"]], "first": 2})
    page1 = body["data"]["sharedValuesByIds"][0]["usedBy"]
    page1_ids = [e["node"]["id"] for e in page1["edges"]]

    assert_that(page1["pageInfo"]["hasNextPage"]).described_as(
        "page 1 has next page"
    ).is_true()

    # Get page 2 using cursor
    body = await gql(
        client,
        SHARED_VALUE_USED_BY,
        {"ids": [sv["id"]], "first": 2, "after": page1["pageInfo"]["endCursor"]},
    )
    page2 = body["data"]["sharedValuesByIds"][0]["usedBy"]
    page2_ids = [e["node"]["id"] for e in page2["edges"]]

    assert_that(page2["edges"]).described_as(
        "page 2 should have 1 edge"
    ).is_length(1)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as(
        "page 2 has no next page"
    ).is_false()

    # Pages should not overlap
    assert_that(page1_ids).described_as(
        "page 1 and page 2 ids should not overlap"
    ).does_not_contain(*page2_ids)
