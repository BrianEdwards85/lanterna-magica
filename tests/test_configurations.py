from assertpy import assert_that
from conftest import gql
from lanterna_magica.data.configurations import Configurations
from lanterna_magica.data.utils import SENTINEL_UUID
from utils import create_environment, create_service, create_shared_value, nodes

# -- Mutations --

CREATE_CONFIGURATION = """
mutation CreateConfiguration($input: CreateConfigurationInput!) {
    createConfiguration(input: $input) {
        id
        service { id name }
        environment { id name }
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
query Configurations($serviceId: ID, $environmentId: ID, $includeGlobal: Boolean, $first: Int, $after: String) {
    configurations(serviceId: $serviceId, environmentId: $environmentId, includeGlobal: $includeGlobal, first: $first, after: $after) {
        edges {
            node {
                id
                service { id }
                environment { id }
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
        service { id }
        environment { id }
        body
        isCurrent
        createdAt
    }
}
"""


# -- Helpers --


async def _create_configuration(client, service_id, environment_id, body, substitutions=None):
    variables = {
        "input": {
            "serviceId": service_id,
            "environmentId": environment_id,
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

    cfg = await _create_configuration(client, svc["id"], env["id"], config_body)
    assert_that(cfg["id"]).described_as("configuration id").is_not_none()
    assert_that(cfg["body"]).described_as("configuration body").is_equal_to(config_body)
    assert_that(cfg["isCurrent"]).described_as("new configuration is current").is_true()
    assert_that(cfg["service"]["id"]).described_as("service reference").is_equal_to(svc["id"])
    assert_that(cfg["environment"]["id"]).described_as("environment reference").is_equal_to(
        env["id"]
    )
    assert_that(cfg["createdAt"]).described_as("createdAt timestamp").is_not_none()
    assert_that(cfg["substitutions"]).described_as("no substitutions").is_empty()


async def test_create_configuration_with_substitutions(client):
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "db_password")

    config_body = {"database": {"password": "placeholder"}}
    substitutions = [{"jsonpath": "$.database.password", "sharedValueId": sv["id"]}]

    cfg = await _create_configuration(client, svc["id"], env["id"], config_body, substitutions)
    assert_that(cfg["substitutions"]).described_as("substitutions count").is_length(1)
    sub = cfg["substitutions"][0]
    assert_that(sub["jsonpath"]).described_as("substitution jsonpath").is_equal_to(
        "$.database.password"
    )
    assert_that(sub["sharedValue"]["id"]).described_as("substitution shared value id").is_equal_to(
        sv["id"]
    )


async def test_new_configuration_replaces_current(client):
    svc = await create_service(client)
    env = await create_environment(client)

    cfg1 = await _create_configuration(client, svc["id"], env["id"], {"version": 1})
    cfg2 = await _create_configuration(client, svc["id"], env["id"], {"version": 2})

    assert_that(cfg2["isCurrent"]).described_as("new config is current").is_true()

    # Check cfg1 is no longer current
    body = await gql(client, CONFIGURATION, {"id": cfg1["id"]})
    assert_that(body["data"]["configuration"]["isCurrent"]).described_as(
        "old config no longer current"
    ).is_false()


async def test_configuration_by_id(client):
    svc = await create_service(client)
    env = await create_environment(client)

    cfg = await _create_configuration(client, svc["id"], env["id"], {"key": "value"})
    body = await gql(client, CONFIGURATION, {"id": cfg["id"]})
    found = body["data"]["configuration"]
    assert_that(found["id"]).described_as("fetched configuration id").is_equal_to(cfg["id"])
    assert_that(found["body"]).described_as("fetched configuration body").is_equal_to(
        {"key": "value"}
    )


async def test_configuration_by_id_not_found(client):
    body = await gql(client, CONFIGURATION, {"id": "00000000-0000-0000-0000-ffffffffffff"})
    assert_that(body["data"]["configuration"]).described_as("non-existent id").is_none()


async def test_configurations_list(client):
    svc = await create_service(client)
    env = await create_environment(client)

    cfg1 = await _create_configuration(client, svc["id"], env["id"], {"version": 1})
    cfg2 = await _create_configuration(client, svc["id"], env["id"], {"version": 2})

    body = await gql(client, CONFIGURATIONS)
    items = nodes(body["data"]["configurations"]["edges"])
    assert_that(items).described_as("configurations list").extracting("id").contains(
        cfg1["id"], cfg2["id"]
    )


async def test_configurations_filter_by_service(client):
    svc1 = await create_service(client, "traefik")
    svc2 = await create_service(client, "nginx")
    env = await create_environment(client)

    await _create_configuration(client, svc1["id"], env["id"], {"app": "traefik"})
    await _create_configuration(client, svc2["id"], env["id"], {"app": "nginx"})

    body = await gql(client, CONFIGURATIONS, {"serviceId": svc1["id"]})
    items = nodes(body["data"]["configurations"]["edges"])
    assert_that(items).described_as("configs filtered by service").is_length(1)
    assert_that(items[0]["body"]).described_as("filtered config body").is_equal_to({"app": "traefik"})


async def test_configurations_filter_by_environment(client):
    svc = await create_service(client)
    env1 = await create_environment(client, "production")
    env2 = await create_environment(client, "staging")

    await _create_configuration(client, svc["id"], env1["id"], {"env": "prod"})
    await _create_configuration(client, svc["id"], env2["id"], {"env": "staging"})

    body = await gql(client, CONFIGURATIONS, {"environmentId": env1["id"]})
    items = nodes(body["data"]["configurations"]["edges"])
    assert_that(items).described_as("configs filtered by environment").is_length(1)
    assert_that(items[0]["body"]).described_as("filtered config body").is_equal_to({"env": "prod"})


async def test_configurations_pagination(client):
    svc = await create_service(client)
    env = await create_environment(client)

    for i in range(5):
        await _create_configuration(client, svc["id"], env["id"], {"version": i})

    body = await gql(client, CONFIGURATIONS, {"first": 2})
    page1 = body["data"]["configurations"]
    assert_that(page1["edges"]).described_as("page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as("page 1 has next page").is_true()

    body = await gql(
        client, CONFIGURATIONS, {"first": 2, "after": page1["pageInfo"]["endCursor"]}
    )
    page2 = body["data"]["configurations"]
    assert_that(page2["edges"]).described_as("page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as("page 2 has next page").is_true()

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
        svc["id"],
        env["id"],
        {"database": {"password": "placeholder"}},
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
        svc["id"],
        env["id"],
        {"database": {"host": "placeholder", "port": 0}},
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
        svc["id"],
        env["id"],
        {"database": {"host": "placeholder", "port": 0}},
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
    assert_that(subs).extracting("jsonpath").described_as("substitution jsonpaths").contains(
        "$.database.host", "$.database.port"
    )


# -- includeGlobal Tests --


async def test_configurations_include_global_default(client):
    """By default, filtering by service includes global (sentinel) configs."""
    svc = await create_service(client)
    env = await create_environment(client)

    await _create_configuration(client, svc["id"], env["id"], {"scope": "specific"})
    await _create_configuration(client, SENTINEL_UUID, env["id"], {"scope": "global"})

    body = await gql(client, CONFIGURATIONS, {"serviceId": svc["id"]})
    items = nodes(body["data"]["configurations"]["edges"])
    bodies = [i["body"] for i in items]
    assert_that(bodies).described_as("default includes global").contains(
        {"scope": "specific"}, {"scope": "global"}
    )


async def test_configurations_exclude_global(client):
    """includeGlobal=false filters out sentinel-scoped configs."""
    svc = await create_service(client)
    env = await create_environment(client)

    await _create_configuration(client, svc["id"], env["id"], {"scope": "specific"})
    await _create_configuration(client, SENTINEL_UUID, env["id"], {"scope": "global"})

    body = await gql(
        client, CONFIGURATIONS, {"serviceId": svc["id"], "includeGlobal": False}
    )
    items = nodes(body["data"]["configurations"]["edges"])
    assert_that(items).described_as("exclude global").is_length(1)
    assert_that(items[0]["body"]).is_equal_to({"scope": "specific"})


# -- Data layer return value tests --


async def test_create_configuration_data_layer_returns_substitutions(client, pool):
    """The data layer must include created substitutions in its return value."""
    configs = Configurations(pool)

    svc = await create_service(client, "dl-test-svc")
    env = await create_environment(client, "dl-test-env")
    sv = await create_shared_value(client, "dl-test-sv")

    result = await configs.create_configuration(
        service_id=svc["id"],
        environment_id=env["id"],
        body={"key": "value"},
        substitutions=[{"jsonpath": "$.key", "shared_value_id": sv["id"]}],
    )

    assert_that(result).described_as("result has substitutions key").contains_key("substitutions")
    assert_that(result["substitutions"]).described_as("substitutions count").is_length(1)
    assert_that(result["substitutions"][0]["jsonpath"]).described_as(
        "substitution jsonpath"
    ).is_equal_to("$.key")
    assert_that(str(result["substitutions"][0]["shared_value_id"])).described_as(
        "substitution shared_value_id"
    ).is_equal_to(sv["id"])


async def test_create_configuration_data_layer_returns_empty_substitutions(client, pool):
    """When no substitutions are provided, the data layer returns an empty list."""
    configs = Configurations(pool)

    svc = await create_service(client, "dl-test-svc2")
    env = await create_environment(client, "dl-test-env2")

    result = await configs.create_configuration(
        service_id=svc["id"],
        environment_id=env["id"],
        body={"key": "value"},
    )

    assert_that(result).described_as("result has substitutions key").contains_key("substitutions")
    assert_that(result["substitutions"]).described_as("substitutions is empty").is_empty()


# -- Edge case tests --


async def test_create_configuration_with_empty_object_body(client):
    """An empty JSON object should be accepted as a configuration body."""
    svc = await create_service(client)
    env = await create_environment(client)

    cfg = await _create_configuration(client, svc["id"], env["id"], {})
    assert_that(cfg["body"]).described_as("empty object body").is_equal_to({})


async def test_create_configuration_with_array_body(client):
    """A JSON array should be accepted as a configuration body."""
    svc = await create_service(client)
    env = await create_environment(client)

    cfg = await _create_configuration(client, svc["id"], env["id"], [1, 2, 3])
    assert_that(cfg["body"]).described_as("array body").is_equal_to([1, 2, 3])


async def test_create_configuration_invalid_service_uuid(client):
    env = await create_environment(client)
    body = await gql(
        client,
        CREATE_CONFIGURATION,
        {"input": {"serviceId": "not-a-uuid", "environmentId": env["id"], "body": {}}},
        expect_errors=True,
    )
    assert_that(body).described_as("invalid service uuid rejected").contains_key("errors")


async def test_create_configuration_nonexistent_service(client):
    env = await create_environment(client)
    body = await gql(
        client,
        CREATE_CONFIGURATION,
        {
            "input": {
                "serviceId": "00000000-0000-0000-0000-ffffffffffff",
                "environmentId": env["id"],
                "body": {"key": "value"},
            }
        },
        expect_errors=True,
    )
    assert_that(body).described_as("nonexistent service rejected").contains_key("errors")


async def test_configuration_by_invalid_uuid(client):
    body = await gql(client, CONFIGURATION, {"id": "not-a-uuid"}, expect_errors=True)
    assert_that(body).described_as("invalid uuid rejected").contains_key("errors")
