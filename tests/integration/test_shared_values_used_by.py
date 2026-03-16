from assertpy import assert_that
from conftest import gql
from gql import (
    CREATE_CONFIGURATION_FOR_LOADER,
    SET_REVISION_CURRENT,
    SHARED_VALUE_WITH_REVISIONS,
    SHARED_VALUES_BY_IDS_WITH_USED_BY,
    create_environment,
    create_revision,
    create_service,
    create_shared_value,
)

# -- DataLoader: SharedValue.usedBy --


async def _create_configuration_with_substitution(client, dimension_ids, body_json, substitutions):
    variables = {
        "input": {
            "dimensionIds": dimension_ids,
            "body": body_json,
            "substitutions": substitutions,
        }
    }
    result = await gql(client, CREATE_CONFIGURATION_FOR_LOADER, variables)
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

    body = await gql(client, SHARED_VALUES_BY_IDS_WITH_USED_BY, {"ids": [sv["id"]]})
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
        SHARED_VALUES_BY_IDS_WITH_USED_BY,
        {"ids": [sv1["id"], sv2["id"]]},
    )
    results = {r["id"]: r for r in body["data"]["sharedValuesByIds"]}

    ids_for_sv1 = [e["node"]["id"] for e in results[sv1["id"]]["usedBy"]["edges"]]
    ids_for_sv2 = [e["node"]["id"] for e in results[sv2["id"]]["usedBy"]["edges"]]

    assert_that(ids_for_sv1).described_as("cfg1 should appear in sv1.usedBy").contains(cfg1["id"])
    assert_that(ids_for_sv2).described_as("cfg2 should appear in sv2.usedBy").contains(cfg2["id"])
    assert_that(ids_for_sv1).described_as("cfg2 should not appear in sv1.usedBy").does_not_contain(cfg2["id"])
    assert_that(ids_for_sv2).described_as("cfg1 should not appear in sv2.usedBy").does_not_contain(cfg1["id"])


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

    body = await gql(client, SHARED_VALUES_BY_IDS_WITH_USED_BY, {"ids": [sv["id"]]})
    result = body["data"]["sharedValuesByIds"][0]
    config_ids = [e["node"]["id"] for e in result["usedBy"]["edges"]]

    assert_that(config_ids).described_as(
        "archived config should not appear in usedBy via DataLoader default path"
    ).does_not_contain(cfg["id"])


async def test_used_by_dataloader_empty_for_unreferenced_shared_value(client):
    """usedBy returns empty connection for a shared value with no configurations."""
    sv = await create_shared_value(client, "loader_unreferenced")

    body = await gql(client, SHARED_VALUES_BY_IDS_WITH_USED_BY, {"ids": [sv["id"]]})
    result = body["data"]["sharedValuesByIds"][0]

    assert_that(result["usedBy"]["edges"]).described_as("unreferenced shared value should have empty usedBy").is_empty()
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

    body = await gql(client, SHARED_VALUES_BY_IDS_WITH_USED_BY, {"ids": [sv["id"]]})
    result = body["data"]["sharedValuesByIds"][0]
    config_ids = [e["node"]["id"] for e in result["usedBy"]["edges"]]

    assert_that(config_ids).described_as("configuration should appear in usedBy").contains(cfg["id"])
    assert_that(config_ids.count(cfg["id"])).described_as(
        "configuration with two substitutions to same shared value should appear exactly once"
    ).is_equal_to(1)


# -- Set/Unset revision current tests --


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
    body = await gql(client, SHARED_VALUE_WITH_REVISIONS, {"ids": [sv["id"]], "currentOnly": True})
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
    assert_that(by_id[rev_staging["id"]]["isCurrent"]).described_as("staging unaffected").is_true()
    assert_that(by_id[rev_prod["id"]]["isCurrent"]).described_as("old prod now current").is_true()
    assert_that(by_id[rev_prod2["id"]]["isCurrent"]).described_as("new prod no longer current").is_false()
