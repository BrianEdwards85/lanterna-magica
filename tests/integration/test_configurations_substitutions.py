from assertpy import assert_that
from conftest import gql
from gql import (
    CONFIGURATION_WITH_TYPED_DIMENSIONS,
    CONFIGURATIONS,
    UPDATE_CONFIG_SUBSTITUTION,
    create_configuration,
    create_environment,
    create_service,
    create_shared_value,
)
from utils import nodes

from lanterna_magica.data.configurations import Configurations

# -- Substitution Tests --


async def test_update_config_substitution(client):
    svc = await create_service(client)
    env = await create_environment(client)
    sv1 = await create_shared_value(client, "db_password")
    sv2 = await create_shared_value(client, "db_password_v2")

    cfg = await create_configuration(
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
    assert_that(updated["sharedValue"]["id"]).described_as("substitution shared value updated").is_equal_to(sv2["id"])
    assert_that(updated["jsonpath"]).described_as("jsonpath unchanged").is_equal_to("$.database.password")


async def test_update_config_substitution_targets_single_jsonpath(client):
    """Updating one substitution by jsonpath must not affect other substitutions."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv_host = await create_shared_value(client, "db_host")
    sv_port = await create_shared_value(client, "db_port")
    sv_host_v2 = await create_shared_value(client, "db_host_v2")

    cfg = await create_configuration(
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
    assert_that(updated["sharedValue"]["id"]).described_as("host substitution updated").is_equal_to(sv_host_v2["id"])

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

    cfg = await create_configuration(
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
    assert_that(subs).extracting("jsonpath").described_as("substitution jsonpaths").contains(
        "$.database.host", "$.database.port"
    )


async def test_configuration_dimensions_include_type(client):
    """Configuration.dimensions should resolve nested type via DimensionTypeLoader."""
    svc = await create_service(client)
    env = await create_environment(client)
    cfg = await create_configuration(client, [svc["id"], env["id"]], {"k": "v"})

    body = await gql(client, CONFIGURATION_WITH_TYPED_DIMENSIONS, {"ids": [cfg["id"]]})
    config = body["data"]["configurationsByIds"][0]
    for dim in config["dimensions"]:
        assert_that(dim["type"]).described_as("dimension has type").contains_key("id", "name")
        assert_that(dim["type"]["name"]).described_as("type name").is_in("service", "environment")


async def test_configuration_substitutions_resolve_nested(client):
    """ConfigSubstitution should resolve configuration and sharedValue loaders."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "db_host")

    cfg = await create_configuration(
        client,
        [svc["id"], env["id"]],
        {"host": "_"},
        [{"jsonpath": "$.host", "sharedValueId": sv["id"]}],
    )

    body = await gql(client, CONFIGURATION_WITH_TYPED_DIMENSIONS, {"ids": [cfg["id"]]})
    subs = body["data"]["configurationsByIds"][0]["substitutions"]
    assert_that(subs).described_as("substitutions count").is_length(1)
    assert_that(subs[0]["configuration"]["id"]).described_as("sub -> config id").is_equal_to(cfg["id"])
    assert_that(subs[0]["sharedValue"]["id"]).described_as("sub -> shared value id").is_equal_to(sv["id"])
    assert_that(subs[0]["sharedValue"]["name"]).described_as("sub -> shared value name").is_equal_to("db_host")


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
    assert_that(body).described_as("not-found substitution update").contains_key("errors")


# -- Data layer substitution tests --


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

    assert_that(result).described_as("result has substitutions key").contains_key("substitutions")
    assert_that(result["substitutions"]).described_as("substitutions count").is_length(1)
    assert_that(result["substitutions"][0]["jsonpath"]).described_as("substitution jsonpath").is_equal_to("$.key")
    assert_that(str(result["substitutions"][0]["shared_value_id"])).described_as(
        "substitution shared_value_id"
    ).is_equal_to(sv["id"])


async def test_create_configuration_data_layer_returns_empty_substitutions(client, pool):
    """When no substitutions are provided, the data layer returns an empty list."""
    configs = Configurations(pool)

    svc = await create_service(client, "dl-test-svc2")
    env = await create_environment(client, "dl-test-env2")

    result = await configs.create_configuration(
        dimension_ids=[svc["id"], env["id"]],
        body={"key": "value"},
    )

    assert_that(result).described_as("result has substitutions key").contains_key("substitutions")
    assert_that(result["substitutions"]).described_as("substitutions is empty").is_empty()
