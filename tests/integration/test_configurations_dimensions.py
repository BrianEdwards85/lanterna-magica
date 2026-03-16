from assertpy import assert_that
from conftest import gql
from gql import (
    CONFIGURATION_WITH_TYPED_DIMENSIONS,
    CONFIGURATIONS,
    CONFIGURATIONS_BY_IDS,
    create_configuration,
    create_dimension_type,
    create_environment,
    create_service,
)
from utils import nodes

# -- includeBase Tests --


async def test_configurations_include_base_default(client, pool):
    """By default, filtering by dimension includes base dimension configs."""
    svc = await create_service(client)
    env = await create_environment(client)

    # Get the base service dimension
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT d.id FROM dimensions d JOIN dimension_types dt ON d.type_id = dt.id"
            " WHERE dt.name = 'service' AND d.base = true"
        )
        base_svc_id = str(row["id"])

    await create_configuration(client, [svc["id"], env["id"]], {"scope": "specific"})
    await create_configuration(client, [base_svc_id, env["id"]], {"scope": "base"})

    body = await gql(client, CONFIGURATIONS, {"dimensionIds": [svc["id"]]})
    items = nodes(body["data"]["configurations"]["edges"])
    bodies = [i["body"] for i in items]
    assert_that(bodies).described_as("default includes base").contains({"scope": "specific"}, {"scope": "base"})


async def test_configurations_exclude_base(client, pool):
    """includeBase=false filters out base-dimension configs."""
    svc = await create_service(client)
    env = await create_environment(client)

    # Get the base service dimension
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT d.id FROM dimensions d JOIN dimension_types dt ON d.type_id = dt.id"
            " WHERE dt.name = 'service' AND d.base = true"
        )
        base_svc_id = str(row["id"])

    await create_configuration(client, [svc["id"], env["id"]], {"scope": "specific"})
    await create_configuration(client, [base_svc_id, env["id"]], {"scope": "base"})

    body = await gql(client, CONFIGURATIONS, {"dimensionIds": [svc["id"]], "includeBase": False})
    items = nodes(body["data"]["configurations"]["edges"])
    assert_that(items).described_as("exclude base").is_length(1)
    assert_that(items[0]["body"]).is_equal_to({"scope": "specific"})


async def test_create_configuration_with_empty_object_body(client):
    """An empty JSON object should be accepted as a configuration body."""
    svc = await create_service(client)
    env = await create_environment(client)

    cfg = await create_configuration(client, [svc["id"], env["id"]], {})
    assert_that(cfg["body"]).described_as("empty object body").is_equal_to({})


async def test_create_configuration_with_array_body(client):
    """A JSON array should be accepted as a configuration body."""
    svc = await create_service(client)
    env = await create_environment(client)

    cfg = await create_configuration(client, [svc["id"], env["id"]], [1, 2, 3])
    assert_that(cfg["body"]).described_as("array body").is_equal_to([1, 2, 3])


# -- Base dimension auto-population tests --


async def test_create_configuration_empty_dimensions_assigns_base(client):
    """Creating a config with no dimensions should auto-assign all base dimensions."""
    cfg = await create_configuration(client, [], {"key": "value"})

    assert_that(cfg["body"]).described_as("configuration body").is_equal_to({"key": "value"})
    assert_that(cfg["isCurrent"]).described_as("configuration is current").is_true()
    dim_names = [d["name"] for d in cfg["dimensions"]]
    assert_that(dim_names).described_as("empty dimensionIds should resolve to base dimensions").contains("global")
    assert_that(cfg["dimensions"]).described_as("should have one base dimension per type").is_length(2)


async def test_base_configuration_appears_in_unfiltered_list(client):
    """A config created with empty dimensions should appear in unfiltered queries."""
    cfg = await create_configuration(client, [], {"key": "value"})

    body = await gql(client, CONFIGURATIONS)
    items = nodes(body["data"]["configurations"]["edges"])
    assert_that(items).described_as("unfiltered configs include base").is_length(1)
    assert_that(items[0]["id"]).described_as("config id matches").is_equal_to(cfg["id"])


async def test_new_base_configuration_replaces_current_base(client):
    """Creating a second config with empty dims should replace the first."""
    cfg1 = await create_configuration(client, [], {"version": 1})
    cfg2 = await create_configuration(client, [], {"version": 2})

    assert_that(cfg2["isCurrent"]).described_as("new base config is current").is_true()

    body = await gql(client, CONFIGURATIONS_BY_IDS, {"ids": [cfg1["id"]]})
    assert_that(body["data"]["configurationsByIds"][0]["isCurrent"]).described_as(
        "old base config no longer current"
    ).is_false()


async def test_new_dimension_type_backfills_base_into_configurations(client):
    """Adding a new dimension type should backfill base dim into existing configs."""
    cfg_before = await create_configuration(client, [], {"before": True})

    await create_dimension_type(client, "region")

    body = await gql(client, CONFIGURATION_WITH_TYPED_DIMENSIONS, {"ids": [cfg_before["id"]]})
    config = body["data"]["configurationsByIds"][0]
    type_names = sorted(d["type"]["name"] for d in config["dimensions"])
    assert_that(type_names).described_as("old configuration now includes all base dimensions").is_equal_to(
        ["environment", "region", "service"]
    )

    # A new empty-dimensions config should replace the old one as current (same scope)
    cfg_after = await create_configuration(client, [], {"after": True})
    assert_that(cfg_after["isCurrent"]).described_as("new config is current").is_true()

    body = await gql(client, CONFIGURATIONS_BY_IDS, {"ids": [cfg_before["id"]]})
    assert_that(body["data"]["configurationsByIds"][0]["isCurrent"]).described_as(
        "old base config replaced as current"
    ).is_false()


# -- Partial dimension tests --


async def test_partial_dimensions_fills_missing_with_global(client):
    """Specifying only some dimensions should fill the rest with globals."""
    svc = await create_service(client)

    cfg = await create_configuration(client, [svc["id"]], {"k": "v"})
    dim_names = {d["name"] for d in cfg["dimensions"]}
    assert_that(dim_names).described_as("should include specified service and global environment").contains(
        svc["name"], "global"
    )
    assert_that(cfg["dimensions"]).described_as("one per dimension type").is_length(2)


async def test_partial_dimensions_env_only(client):
    """Specifying only environment should fill service with global."""
    env = await create_environment(client)

    cfg = await create_configuration(client, [env["id"]], {"k": "v"})

    body = await gql(
        client,
        CONFIGURATION_WITH_TYPED_DIMENSIONS,
        {"ids": [cfg["id"]]},
    )
    config = body["data"]["configurationsByIds"][0]
    by_type = {d["type"]["name"]: d["name"] for d in config["dimensions"]}
    assert_that(by_type).described_as("types covered").contains_key("service", "environment")
    assert_that(by_type["service"]).described_as("service auto-filled with global").is_equal_to("global")
    assert_that(by_type["environment"]).described_as("environment is the one we specified").is_equal_to(env["name"])
