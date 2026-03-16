from assertpy import assert_that
from conftest import gql
from gql import (
    CONFIGURATION_WITH_PROJECTION,
    CONFIGURATIONS_BY_IDS,
    CREATE_CONFIGURATION,
    SET_CONFIGURATION_CURRENT,
    create_configuration,
    create_environment,
    create_revision,
    create_service,
    create_shared_value,
)

# -- Set/Unset configuration current tests --


async def test_set_noncurrent_configuration_to_current(client):
    """Making a non-current configuration current should unset the old current."""
    svc = await create_service(client)
    env = await create_environment(client)

    cfg1 = await create_configuration(client, [svc["id"], env["id"]], {"v": 1})
    cfg2 = await create_configuration(client, [svc["id"], env["id"]], {"v": 2})

    # cfg1 is not current, cfg2 is current — make cfg1 current again
    body = await gql(client, SET_CONFIGURATION_CURRENT, {"id": cfg1["id"], "isCurrent": True})
    result = body["data"]["setConfigurationCurrent"]
    assert_that(result["id"]).is_equal_to(cfg1["id"])
    assert_that(result["isCurrent"]).described_as("cfg1 now current").is_true()

    # Verify cfg2 is no longer current
    body = await gql(client, CONFIGURATIONS_BY_IDS, {"ids": [cfg2["id"]]})
    assert_that(body["data"]["configurationsByIds"][0]["isCurrent"]).described_as("cfg2 no longer current").is_false()


async def test_deactivate_current_configuration(client):
    """Unsetting current should leave no current configuration for that scope."""
    svc = await create_service(client)
    env = await create_environment(client)

    cfg = await create_configuration(client, [svc["id"], env["id"]], {"v": 1})

    body = await gql(client, SET_CONFIGURATION_CURRENT, {"id": cfg["id"], "isCurrent": False})
    result = body["data"]["setConfigurationCurrent"]
    assert_that(result["isCurrent"]).described_as("configuration deactivated").is_false()


async def test_set_current_only_affects_same_scope_configurations(client):
    """Setting current should only unset configurations with the same scope."""
    svc = await create_service(client)
    env1 = await create_environment(client, "production")
    env2 = await create_environment(client, "staging")

    cfg_prod = await create_configuration(client, [svc["id"], env1["id"]], {"env": "prod"})
    cfg_staging = await create_configuration(client, [svc["id"], env2["id"]], {"env": "staging"})

    # Both should be current (different scopes)
    assert_that(cfg_prod["isCurrent"]).is_true()
    assert_that(cfg_staging["isCurrent"]).is_true()

    # Add a second prod config, then re-activate the first
    await create_configuration(client, [svc["id"], env1["id"]], {"env": "prod2"})
    await gql(client, SET_CONFIGURATION_CURRENT, {"id": cfg_prod["id"], "isCurrent": True})

    # Staging should still be current
    body = await gql(client, CONFIGURATIONS_BY_IDS, {"ids": [cfg_staging["id"]]})
    assert_that(body["data"]["configurationsByIds"][0]["isCurrent"]).described_as("staging unaffected").is_true()


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

    cfg = await create_configuration(
        client,
        [svc["id"], env["id"]],
        {"x": "_"},
        [{"jsonpath": "$.x", "sharedValueId": sv["id"]}],
    )
    assert_that(cfg["id"]).described_as("configuration id").is_not_none()
    assert_that(cfg["substitutions"]).described_as("substitutions count").is_length(1)
    assert_that(cfg["substitutions"][0]["jsonpath"]).described_as("substitution jsonpath").is_equal_to("$.x")


async def test_create_configuration_missing_substitution_for_sentinel_raises_error(
    client,
):
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
    assert_that(error_message).described_as("error mentions missing path").contains("$.x")


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
    assert_that(error_message).described_as("error mentions extra path").contains("$.y")


# -- Projection field tests --


async def test_projection_with_resolved_substitution(client):
    """projection returns body with sentinel replaced by the current revision value."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "db_password")

    # Create a revision scoped to svc+env and mark it current
    await create_revision(client, sv["id"], [svc["id"], env["id"]], "s3cr3t")

    cfg = await create_configuration(
        client,
        [svc["id"], env["id"]],
        {"database": {"password": "_"}},
        [{"jsonpath": "$.database.password", "sharedValueId": sv["id"]}],
    )

    body = await gql(client, CONFIGURATION_WITH_PROJECTION, {"ids": [cfg["id"]]})
    config = body["data"]["configurationsByIds"][0]
    assert_that(config["projection"]).described_as("projection replaces sentinel with resolved value").is_equal_to(
        {"database": {"password": "s3cr3t"}}
    )
    assert_that(config["body"]).described_as("original body unchanged").is_equal_to({"database": {"password": "_"}})


async def test_projection_with_no_substitutions(client):
    """projection on a configuration with no substitutions returns the body unchanged."""
    svc = await create_service(client)
    env = await create_environment(client)

    cfg = await create_configuration(
        client,
        [svc["id"], env["id"]],
        {"host": "localhost", "port": 5432},
    )

    body = await gql(client, CONFIGURATION_WITH_PROJECTION, {"ids": [cfg["id"]]})
    config = body["data"]["configurationsByIds"][0]
    assert_that(config["projection"]).described_as("projection equals body when no substitutions").is_equal_to(
        {"host": "localhost", "port": 5432}
    )


async def test_projection_with_unresolvable_substitution_leaves_sentinel(client):
    """When a substitution has no current revision for the scope, projection leaves '_'."""
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "unresolved_secret")

    # No revision created — substitution cannot be resolved
    cfg = await create_configuration(
        client,
        [svc["id"], env["id"]],
        {"api_key": "_"},
        [{"jsonpath": "$.api_key", "sharedValueId": sv["id"]}],
    )

    body = await gql(client, CONFIGURATION_WITH_PROJECTION, {"ids": [cfg["id"]]})
    config = body["data"]["configurationsByIds"][0]
    assert_that(config["projection"]).described_as(
        "unresolvable substitution keeps sentinel in projection"
    ).is_equal_to({"api_key": "_"})


# -- Type uniqueness validation tests --


async def test_create_configuration_duplicate_dimension_type_raises_error(client):
    """Creating a configuration with two dimensions of the same type should fail."""
    svc1 = await create_service(client, "svc-alpha")
    svc2 = await create_service(client, "svc-beta")

    body = await gql(
        client,
        CREATE_CONFIGURATION,
        {
            "input": {
                "dimensionIds": [svc1["id"], svc2["id"]],
                "body": {"key": "value"},
            }
        },
        expect_errors=True,
    )
    assert_that(body).described_as("duplicate type error response").contains_key("errors")
    error_message = body["errors"][0]["message"]
    assert_that(error_message).described_as("error mentions duplicate type").contains(
        "multiple dimensions of the same type"
    )
