from assertpy import assert_that
from conftest import gql
from utils import (
    create_dimension_type,
    create_environment,
    create_revision,
    create_service,
    create_shared_value,
    nodes,
)

from lanterna_magica.data.configurations import Configurations

# -- Mutations --

CREATE_CONFIGURATION = """
mutation CreateConfiguration($input: CreateConfigurationInput!) {
    createConfiguration(input: $input) {
        id
        dimensions { id name }
        body
        isCurrent
        createdAt
        substitutions {
            id jsonpath sharedValue { id name } createdAt
        }
    }
}
"""

UPDATE_CONFIG_SUBSTITUTION = """
mutation UpdateConfigSubstitution($input: SetConfigSubstitutionInput!) {
    updateConfigSubstitution(input: $input) {
        id
        configuration { id }
        jsonpath
        sharedValue { id name }
        createdAt
    }
}
"""

# Substitution query helper for verifying updates
CONFIGURATION_WITH_SUBS = """
query Configuration($id: ID!) {
    configuration(id: $id) {
        id
        substitutions {
            id jsonpath sharedValue { id }
        }
    }
}
"""

# -- Queries --

CONFIGURATIONS = """
query Configurations($dimensionIds: [ID!], $includeBase: Boolean, $first: Int, $after: String) {
    configurations(dimensionIds: $dimensionIds, includeBase: $includeBase, first: $first, after: $after) {
        edges {
            node {
                id
                dimensions { id name }
                body
                isCurrent
                createdAt
                substitutions {
                    id jsonpath sharedValue { id }
                }
            }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

CONFIGURATION = """
query Configuration($id: ID!) {
    configuration(id: $id) {
        id
        dimensions { id name }
        body
        isCurrent
        createdAt
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


# -- Configuration CRUD Tests --


async def test_create_configuration(client):
    svc = await create_service(client)
    env = await create_environment(client)
    config_body = {"host": "localhost", "port": 8080}

    cfg = await _create_configuration(client, [svc["id"], env["id"]], config_body)
    assert_that(cfg["id"]).described_as("configuration id").is_not_none()
    assert_that(cfg["body"]).described_as("configuration body").is_equal_to(config_body)
    assert_that(cfg["isCurrent"]).described_as("new configuration is current").is_true()
    dim_ids = [d["id"] for d in cfg["dimensions"]]
    assert_that(dim_ids).described_as("dimension references").contains(
        svc["id"], env["id"]
    )
    assert_that(cfg["createdAt"]).described_as("createdAt timestamp").is_not_none()
    assert_that(cfg["substitutions"]).described_as("no substitutions").is_empty()


async def test_create_configuration_with_substitutions(client):
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "db_password")

    config_body = {"database": {"password": "_"}}
    substitutions = [{"jsonpath": "$.database.password", "sharedValueId": sv["id"]}]

    cfg = await _create_configuration(
        client, [svc["id"], env["id"]], config_body, substitutions
    )
    assert_that(cfg["substitutions"]).described_as("substitutions count").is_length(1)
    sub = cfg["substitutions"][0]
    assert_that(sub["jsonpath"]).described_as("substitution jsonpath").is_equal_to(
        "$.database.password"
    )
    assert_that(sub["sharedValue"]["id"]).described_as(
        "substitution shared value id"
    ).is_equal_to(sv["id"])


async def test_new_configuration_replaces_current(client):
    svc = await create_service(client)
    env = await create_environment(client)

    cfg1 = await _create_configuration(client, [svc["id"], env["id"]], {"version": 1})
    cfg2 = await _create_configuration(client, [svc["id"], env["id"]], {"version": 2})

    assert_that(cfg2["isCurrent"]).described_as("new config is current").is_true()

    # Check cfg1 is no longer current
    body = await gql(client, CONFIGURATION, {"id": cfg1["id"]})
    assert_that(body["data"]["configuration"]["isCurrent"]).described_as(
        "old config no longer current"
    ).is_false()


async def test_configuration_by_id(client):
    svc = await create_service(client)
    env = await create_environment(client)

    cfg = await _create_configuration(client, [svc["id"], env["id"]], {"key": "value"})
    body = await gql(client, CONFIGURATION, {"id": cfg["id"]})
    found = body["data"]["configuration"]
    assert_that(found["id"]).described_as("fetched configuration id").is_equal_to(
        cfg["id"]
    )
    assert_that(found["body"]).described_as("fetched configuration body").is_equal_to(
        {"key": "value"}
    )


async def test_configuration_by_id_not_found(client):
    body = await gql(
        client, CONFIGURATION, {"id": "00000000-0000-0000-0000-ffffffffffff"}
    )
    assert_that(body["data"]["configuration"]).described_as("non-existent id").is_none()


async def test_configurations_list(client):
    svc = await create_service(client)
    env = await create_environment(client)

    cfg1 = await _create_configuration(client, [svc["id"], env["id"]], {"version": 1})
    cfg2 = await _create_configuration(client, [svc["id"], env["id"]], {"version": 2})

    body = await gql(client, CONFIGURATIONS)
    items = nodes(body["data"]["configurations"]["edges"])
    assert_that(items).described_as("configurations list").extracting("id").contains(
        cfg1["id"], cfg2["id"]
    )


async def test_configurations_filter_by_dimension(client):
    svc1 = await create_service(client, "traefik")
    svc2 = await create_service(client, "nginx")
    env = await create_environment(client)

    await _create_configuration(client, [svc1["id"], env["id"]], {"app": "traefik"})
    await _create_configuration(client, [svc2["id"], env["id"]], {"app": "nginx"})

    body = await gql(client, CONFIGURATIONS, {"dimensionIds": [svc1["id"]]})
    items = nodes(body["data"]["configurations"]["edges"])
    assert_that(items).described_as("configs filtered by dimension").is_length(1)
    assert_that(items[0]["body"]).described_as("filtered config body").is_equal_to(
        {"app": "traefik"}
    )


async def test_configurations_pagination(client):
    svc = await create_service(client)
    env = await create_environment(client)

    for i in range(5):
        await _create_configuration(client, [svc["id"], env["id"]], {"version": i})

    body = await gql(client, CONFIGURATIONS, {"first": 2})
    page1 = body["data"]["configurations"]
    assert_that(page1["edges"]).described_as("page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as(
        "page 1 has next page"
    ).is_true()

    body = await gql(
        client, CONFIGURATIONS, {"first": 2, "after": page1["pageInfo"]["endCursor"]}
    )
    page2 = body["data"]["configurations"]
    assert_that(page2["edges"]).described_as("page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as(
        "page 2 has next page"
    ).is_true()

    body = await gql(
        client, CONFIGURATIONS, {"first": 2, "after": page2["pageInfo"]["endCursor"]}
    )
    page3 = body["data"]["configurations"]
    assert_that(page3["edges"]).described_as("page 3 edge count").is_length(1)
    assert_that(page3["pageInfo"]["hasNextPage"]).described_as(
        "page 3 has no next page"
    ).is_false()


# -- Substitution Tests --


async def test_update_config_substitution(client):
    svc = await create_service(client)
    env = await create_environment(client)
    sv1 = await create_shared_value(client, "db_password")
    sv2 = await create_shared_value(client, "db_password_v2")

    cfg = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"database": {"password": "_"}},
        [{"jsonpath": "$.database.password", "sharedValueId": sv1["id"]}],
    )

    body = await gql(
        client,
        UPDATE_CONFIG_SUBSTITUTION,
        {
            "input": {
                "configurationId": cfg["id"],
                "jsonpath": "$.database.password",
                "sharedValueId": sv2["id"],
            }
        },
    )
    updated = body["data"]["updateConfigSubstitution"]
    assert_that(updated["sharedValue"]["id"]).described_as(
        "substitution shared value updated"
    ).is_equal_to(sv2["id"])
    assert_that(updated["jsonpath"]).described_as("jsonpath unchanged").is_equal_to(
        "$.database.password"
    )


async def test_update_config_substitution_targets_single_jsonpath(client):
    """Updating one substitution by jsonpath must not affect other substitutions."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv_host = await create_shared_value(client, "db_host")
    sv_port = await create_shared_value(client, "db_port")
    sv_host_v2 = await create_shared_value(client, "db_host_v2")

    cfg = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"database": {"host": "_", "port": "_"}},
        [
            {"jsonpath": "$.database.host", "sharedValueId": sv_host["id"]},
            {"jsonpath": "$.database.port", "sharedValueId": sv_port["id"]},
        ],
    )

    # Update only the host substitution
    body = await gql(
        client,
        UPDATE_CONFIG_SUBSTITUTION,
        {
            "input": {
                "configurationId": cfg["id"],
                "jsonpath": "$.database.host",
                "sharedValueId": sv_host_v2["id"],
            }
        },
    )
    updated = body["data"]["updateConfigSubstitution"]
    assert_that(updated["sharedValue"]["id"]).described_as(
        "host substitution updated"
    ).is_equal_to(sv_host_v2["id"])

    # Verify the port substitution was NOT changed
    body = await gql(client, CONFIGURATIONS)
    items = nodes(body["data"]["configurations"]["edges"])
    config_node = next(n for n in items if n["id"] == cfg["id"])
    subs_by_path = {s["jsonpath"]: s for s in config_node["substitutions"]}

    assert_that(subs_by_path["$.database.port"]["sharedValue"]["id"]).described_as(
        "port substitution should be unchanged"
    ).is_equal_to(sv_port["id"])
    assert_that(subs_by_path["$.database.host"]["sharedValue"]["id"]).described_as(
        "host substitution should be updated"
    ).is_equal_to(sv_host_v2["id"])


async def test_configuration_substitutions_field(client):
    svc = await create_service(client)
    env = await create_environment(client)
    sv1 = await create_shared_value(client, "db_host")
    sv2 = await create_shared_value(client, "db_port")

    cfg = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"database": {"host": "_", "port": "_"}},
        [
            {"jsonpath": "$.database.host", "sharedValueId": sv1["id"]},
            {"jsonpath": "$.database.port", "sharedValueId": sv2["id"]},
        ],
    )

    # Query the configuration and verify substitutions are returned
    body = await gql(client, CONFIGURATIONS)
    items = nodes(body["data"]["configurations"]["edges"])
    config_node = next(n for n in items if n["id"] == cfg["id"])
    subs = config_node["substitutions"]
    assert_that(subs).described_as("substitutions count").is_length(2)
    assert_that(subs).extracting("jsonpath").described_as(
        "substitution jsonpaths"
    ).contains("$.database.host", "$.database.port")


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

    await _create_configuration(client, [svc["id"], env["id"]], {"scope": "specific"})
    await _create_configuration(client, [base_svc_id, env["id"]], {"scope": "base"})

    body = await gql(client, CONFIGURATIONS, {"dimensionIds": [svc["id"]]})
    items = nodes(body["data"]["configurations"]["edges"])
    bodies = [i["body"] for i in items]
    assert_that(bodies).described_as("default includes base").contains(
        {"scope": "specific"}, {"scope": "base"}
    )


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

    await _create_configuration(client, [svc["id"], env["id"]], {"scope": "specific"})
    await _create_configuration(client, [base_svc_id, env["id"]], {"scope": "base"})

    body = await gql(
        client, CONFIGURATIONS, {"dimensionIds": [svc["id"]], "includeBase": False}
    )
    items = nodes(body["data"]["configurations"]["edges"])
    assert_that(items).described_as("exclude base").is_length(1)
    assert_that(items[0]["body"]).is_equal_to({"scope": "specific"})


# -- Data layer return value tests --


async def test_create_configuration_data_layer_returns_substitutions(client, pool):
    """The data layer must include created substitutions in its return value."""
    configs = Configurations(pool)

    svc = await create_service(client, "dl-test-svc")
    env = await create_environment(client, "dl-test-env")
    sv = await create_shared_value(client, "dl-test-sv")

    result = await configs.create_configuration(
        dimension_ids=[svc["id"], env["id"]],
        body={"key": "value"},
        substitutions=[{"jsonpath": "$.key", "shared_value_id": sv["id"]}],
    )

    assert_that(result).described_as("result has substitutions key").contains_key(
        "substitutions"
    )
    assert_that(result["substitutions"]).described_as("substitutions count").is_length(
        1
    )
    assert_that(result["substitutions"][0]["jsonpath"]).described_as(
        "substitution jsonpath"
    ).is_equal_to("$.key")
    assert_that(str(result["substitutions"][0]["shared_value_id"])).described_as(
        "substitution shared_value_id"
    ).is_equal_to(sv["id"])


async def test_create_configuration_data_layer_returns_empty_substitutions(
    client, pool
):
    """When no substitutions are provided, the data layer returns an empty list."""
    configs = Configurations(pool)

    svc = await create_service(client, "dl-test-svc2")
    env = await create_environment(client, "dl-test-env2")

    result = await configs.create_configuration(
        dimension_ids=[svc["id"], env["id"]],
        body={"key": "value"},
    )

    assert_that(result).described_as("result has substitutions key").contains_key(
        "substitutions"
    )
    assert_that(result["substitutions"]).described_as(
        "substitutions is empty"
    ).is_empty()


# -- Edge case tests --


async def test_create_configuration_with_empty_object_body(client):
    """An empty JSON object should be accepted as a configuration body."""
    svc = await create_service(client)
    env = await create_environment(client)

    cfg = await _create_configuration(client, [svc["id"], env["id"]], {})
    assert_that(cfg["body"]).described_as("empty object body").is_equal_to({})


async def test_create_configuration_with_array_body(client):
    """A JSON array should be accepted as a configuration body."""
    svc = await create_service(client)
    env = await create_environment(client)

    cfg = await _create_configuration(client, [svc["id"], env["id"]], [1, 2, 3])
    assert_that(cfg["body"]).described_as("array body").is_equal_to([1, 2, 3])


async def test_configuration_by_invalid_uuid(client):
    body = await gql(client, CONFIGURATION, {"id": "not-a-uuid"}, expect_errors=True)
    assert_that(body).described_as("invalid uuid rejected").contains_key("errors")


# -- Nested relationship / loader tests --


CONFIGURATION_WITH_TYPED_DIMENSIONS = """
query Configuration($id: ID!) {
    configuration(id: $id) {
        id
        dimensions { id name type { id name } }
        substitutions {
            id jsonpath
            configuration { id }
            sharedValue { id name }
        }
    }
}
"""


async def test_configuration_dimensions_include_type(client):
    """Configuration.dimensions should resolve nested type via DimensionTypeLoader."""
    svc = await create_service(client)
    env = await create_environment(client)
    cfg = await _create_configuration(client, [svc["id"], env["id"]], {"k": "v"})

    body = await gql(client, CONFIGURATION_WITH_TYPED_DIMENSIONS, {"id": cfg["id"]})
    config = body["data"]["configuration"]
    for dim in config["dimensions"]:
        assert_that(dim["type"]).described_as("dimension has type").contains_key(
            "id", "name"
        )
        assert_that(dim["type"]["name"]).described_as("type name").is_in(
            "service", "environment"
        )


async def test_configuration_substitutions_resolve_nested(client):
    """ConfigSubstitution should resolve configuration and sharedValue loaders."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "db_host")

    cfg = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"host": "_"},
        [{"jsonpath": "$.host", "sharedValueId": sv["id"]}],
    )

    body = await gql(client, CONFIGURATION_WITH_TYPED_DIMENSIONS, {"id": cfg["id"]})
    subs = body["data"]["configuration"]["substitutions"]
    assert_that(subs).described_as("substitutions count").is_length(1)
    assert_that(subs[0]["configuration"]["id"]).described_as(
        "sub -> config id"
    ).is_equal_to(cfg["id"])
    assert_that(subs[0]["sharedValue"]["id"]).described_as(
        "sub -> shared value id"
    ).is_equal_to(sv["id"])
    assert_that(subs[0]["sharedValue"]["name"]).described_as(
        "sub -> shared value name"
    ).is_equal_to("db_host")


async def test_update_config_substitution_not_found(client):
    """Updating a substitution for a nonexistent config/jsonpath should error."""
    sv = await create_shared_value(client, "db_host")
    body = await gql(
        client,
        UPDATE_CONFIG_SUBSTITUTION,
        {
            "input": {
                "configurationId": "00000000-0000-0000-0000-ffffffffffff",
                "jsonpath": "$.nope",
                "sharedValueId": sv["id"],
            }
        },
        expect_errors=True,
    )
    assert_that(body).described_as("not-found substitution update").contains_key(
        "errors"
    )


# -- Base dimension auto-population tests --


async def test_create_configuration_empty_dimensions_assigns_base(client):
    """Creating a config with no dimensions should auto-assign all base dimensions."""
    cfg = await _create_configuration(client, [], {"key": "value"})

    assert_that(cfg["body"]).described_as("configuration body").is_equal_to(
        {"key": "value"}
    )
    assert_that(cfg["isCurrent"]).described_as("configuration is current").is_true()
    dim_names = [d["name"] for d in cfg["dimensions"]]
    assert_that(dim_names).described_as(
        "empty dimensionIds should resolve to base dimensions"
    ).contains("global")
    assert_that(cfg["dimensions"]).described_as(
        "should have one base dimension per type"
    ).is_length(2)


async def test_base_configuration_appears_in_unfiltered_list(client):
    """A config created with empty dimensions should appear in unfiltered queries."""
    cfg = await _create_configuration(client, [], {"key": "value"})

    body = await gql(client, CONFIGURATIONS)
    items = nodes(body["data"]["configurations"]["edges"])
    assert_that(items).described_as("unfiltered configs include base").is_length(1)
    assert_that(items[0]["id"]).described_as("config id matches").is_equal_to(cfg["id"])


async def test_new_base_configuration_replaces_current_base(client):
    """Creating a second config with empty dims should replace the first."""
    cfg1 = await _create_configuration(client, [], {"version": 1})
    cfg2 = await _create_configuration(client, [], {"version": 2})

    assert_that(cfg2["isCurrent"]).described_as("new base config is current").is_true()

    body = await gql(client, CONFIGURATION, {"id": cfg1["id"]})
    assert_that(body["data"]["configuration"]["isCurrent"]).described_as(
        "old base config no longer current"
    ).is_false()


async def test_new_dimension_type_backfills_base_into_configurations(client):
    """Adding a new dimension type should backfill base dim into existing configs."""
    cfg_before = await _create_configuration(client, [], {"before": True})

    await create_dimension_type(client, "region")

    body = await gql(
        client, CONFIGURATION_WITH_TYPED_DIMENSIONS, {"id": cfg_before["id"]}
    )
    config = body["data"]["configuration"]
    type_names = sorted(d["type"]["name"] for d in config["dimensions"])
    assert_that(type_names).described_as(
        "old configuration now includes all base dimensions"
    ).is_equal_to(["environment", "region", "service"])

    # A new empty-dimensions config should replace the old one as current (same scope)
    cfg_after = await _create_configuration(client, [], {"after": True})
    assert_that(cfg_after["isCurrent"]).described_as("new config is current").is_true()

    body = await gql(client, CONFIGURATION, {"id": cfg_before["id"]})
    assert_that(body["data"]["configuration"]["isCurrent"]).described_as(
        "old base config replaced as current"
    ).is_false()


async def test_partial_dimensions_fills_missing_with_global(client):
    """Specifying only some dimensions should fill the rest with globals."""
    svc = await create_service(client)

    cfg = await _create_configuration(client, [svc["id"]], {"k": "v"})
    dim_names = {d["name"] for d in cfg["dimensions"]}
    assert_that(dim_names).described_as(
        "should include specified service and global environment"
    ).contains(svc["name"], "global")
    assert_that(cfg["dimensions"]).described_as(
        "one per dimension type"
    ).is_length(2)


async def test_partial_dimensions_env_only(client):
    """Specifying only environment should fill service with global."""
    env = await create_environment(client)

    cfg = await _create_configuration(
        client, [env["id"]], {"k": "v"}
    )

    body = await gql(
        client,
        CONFIGURATION_WITH_TYPED_DIMENSIONS,
        {"id": cfg["id"]},
    )
    config = body["data"]["configuration"]
    by_type = {
        d["type"]["name"]: d["name"] for d in config["dimensions"]
    }
    assert_that(by_type).described_as("types covered").contains_key(
        "service", "environment"
    )
    assert_that(by_type["service"]).described_as(
        "service auto-filled with global"
    ).is_equal_to("global")
    assert_that(by_type["environment"]).described_as(
        "environment is the one we specified"
    ).is_equal_to(env["name"])


# -- Set/Unset configuration current tests --

SET_CONFIGURATION_CURRENT = """
mutation SetConfigurationCurrent($id: ID!, $isCurrent: Boolean!) {
    setConfigurationCurrent(id: $id, isCurrent: $isCurrent) {
        id body isCurrent
    }
}
"""


async def test_set_noncurrent_configuration_to_current(client):
    """Making a non-current configuration current should unset the old current."""
    svc = await create_service(client)
    env = await create_environment(client)

    cfg1 = await _create_configuration(client, [svc["id"], env["id"]], {"v": 1})
    cfg2 = await _create_configuration(client, [svc["id"], env["id"]], {"v": 2})

    # cfg1 is not current, cfg2 is current — make cfg1 current again
    body = await gql(client, SET_CONFIGURATION_CURRENT, {"id": cfg1["id"], "isCurrent": True})
    result = body["data"]["setConfigurationCurrent"]
    assert_that(result["id"]).is_equal_to(cfg1["id"])
    assert_that(result["isCurrent"]).described_as("cfg1 now current").is_true()

    # Verify cfg2 is no longer current
    body = await gql(client, CONFIGURATION, {"id": cfg2["id"]})
    assert_that(body["data"]["configuration"]["isCurrent"]).described_as(
        "cfg2 no longer current"
    ).is_false()


async def test_deactivate_current_configuration(client):
    """Unsetting current should leave no current configuration for that scope."""
    svc = await create_service(client)
    env = await create_environment(client)

    cfg = await _create_configuration(client, [svc["id"], env["id"]], {"v": 1})

    body = await gql(client, SET_CONFIGURATION_CURRENT, {"id": cfg["id"], "isCurrent": False})
    result = body["data"]["setConfigurationCurrent"]
    assert_that(result["isCurrent"]).described_as("configuration deactivated").is_false()


async def test_set_current_only_affects_same_scope_configurations(client):
    """Setting current should only unset configurations with the same scope."""
    svc = await create_service(client)
    env1 = await create_environment(client, "production")
    env2 = await create_environment(client, "staging")

    cfg_prod = await _create_configuration(client, [svc["id"], env1["id"]], {"env": "prod"})
    cfg_staging = await _create_configuration(client, [svc["id"], env2["id"]], {"env": "staging"})

    # Both should be current (different scopes)
    assert_that(cfg_prod["isCurrent"]).is_true()
    assert_that(cfg_staging["isCurrent"]).is_true()

    # Add a second prod config, then re-activate the first
    await _create_configuration(client, [svc["id"], env1["id"]], {"env": "prod2"})
    await gql(client, SET_CONFIGURATION_CURRENT, {"id": cfg_prod["id"], "isCurrent": True})

    # Staging should still be current
    body = await gql(client, CONFIGURATION, {"id": cfg_staging["id"]})
    assert_that(body["data"]["configuration"]["isCurrent"]).described_as(
        "staging unaffected"
    ).is_true()


async def test_set_configuration_current_not_found(client):
    """Setting current on a non-existent configuration should error."""
    body = await gql(
        client,
        SET_CONFIGURATION_CURRENT,
        {"id": "00000000-0000-0000-0000-ffffffffffff", "isCurrent": True},
        expect_errors=True,
    )
    assert_that(body).described_as("not found error").contains_key("errors")


# -- Orchestrator validation tests --


async def test_create_configuration_with_sentinel_and_substitution_succeeds(client):
    """Happy path: body with sentinel and matching substitution succeeds."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "my_secret")

    cfg = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"x": "_"},
        [{"jsonpath": "$.x", "sharedValueId": sv["id"]}],
    )
    assert_that(cfg["id"]).described_as("configuration id").is_not_none()
    assert_that(cfg["substitutions"]).described_as("substitutions count").is_length(1)
    assert_that(cfg["substitutions"][0]["jsonpath"]).described_as(
        "substitution jsonpath"
    ).is_equal_to("$.x")


async def test_create_configuration_missing_substitution_for_sentinel_raises_error(client):
    """Body has a sentinel but no substitution provided — should raise ValidationError."""
    svc = await create_service(client)
    env = await create_environment(client)

    body = await gql(
        client,
        CREATE_CONFIGURATION,
        {
            "input": {
                "dimensionIds": [svc["id"], env["id"]],
                "body": {"x": "_"},
            }
        },
        expect_errors=True,
    )
    assert_that(body).described_as("validation error response").contains_key("errors")
    error_message = body["errors"][0]["message"]
    assert_that(error_message).described_as(
        "error mentions missing path"
    ).contains("$.x")


async def test_create_configuration_extra_substitution_path_raises_error(client):
    """Substitution provided for a path that has no sentinel in body — should raise ValidationError."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "unused_secret")

    body = await gql(
        client,
        CREATE_CONFIGURATION,
        {
            "input": {
                "dimensionIds": [svc["id"], env["id"]],
                "body": {"x": 1},
                "substitutions": [{"jsonpath": "$.y", "sharedValueId": sv["id"]}],
            }
        },
        expect_errors=True,
    )
    assert_that(body).described_as("validation error response").contains_key("errors")
    error_message = body["errors"][0]["message"]
    assert_that(error_message).described_as(
        "error mentions extra path"
    ).contains("$.y")


# -- projection field tests --

CONFIGURATION_WITH_PROJECTION = """
query Configuration($id: ID!) {
    configuration(id: $id) {
        id
        body
        projection
    }
}
"""


async def test_projection_with_resolved_substitution(client):
    """projection returns body with sentinel replaced by the current revision value."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "db_password")

    # Create a revision scoped to svc+env and mark it current
    await create_revision(client, sv["id"], [svc["id"], env["id"]], "s3cr3t")

    cfg = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"database": {"password": "_"}},
        [{"jsonpath": "$.database.password", "sharedValueId": sv["id"]}],
    )

    body = await gql(client, CONFIGURATION_WITH_PROJECTION, {"id": cfg["id"]})
    config = body["data"]["configuration"]
    assert_that(config["projection"]).described_as(
        "projection replaces sentinel with resolved value"
    ).is_equal_to({"database": {"password": "s3cr3t"}})
    assert_that(config["body"]).described_as(
        "original body unchanged"
    ).is_equal_to({"database": {"password": "_"}})


async def test_projection_with_no_substitutions(client):
    """projection on a configuration with no substitutions returns the body unchanged."""
    svc = await create_service(client)
    env = await create_environment(client)

    cfg = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"host": "localhost", "port": 5432},
    )

    body = await gql(client, CONFIGURATION_WITH_PROJECTION, {"id": cfg["id"]})
    config = body["data"]["configuration"]
    assert_that(config["projection"]).described_as(
        "projection equals body when no substitutions"
    ).is_equal_to({"host": "localhost", "port": 5432})


async def test_projection_with_unresolvable_substitution_leaves_sentinel(client):
    """When a substitution has no current revision for the scope, projection leaves '_'."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "unresolved_secret")

    # No revision created — substitution cannot be resolved
    cfg = await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"api_key": "_"},
        [{"jsonpath": "$.api_key", "sharedValueId": sv["id"]}],
    )

    body = await gql(client, CONFIGURATION_WITH_PROJECTION, {"id": cfg["id"]})
    config = body["data"]["configuration"]
    assert_that(config["projection"]).described_as(
        "unresolvable substitution keeps sentinel in projection"
    ).is_equal_to({"api_key": "_"})
