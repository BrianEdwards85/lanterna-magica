"""Integration tests for data-layer methods added in turbo-umbrella-1qr.2:
- Dimensions.get_by_type_and_name
- Configurations.get_for_rest_scope
"""

from assertpy import assert_that
from gql import (
    _get_type_id,
    create_configuration,
    create_environment,
    create_service,
    create_shared_value,
)

from lanterna_magica.data.configurations import Configurations
from lanterna_magica.data.dimensions import Dimensions

# ---------------------------------------------------------------------------
# Dimensions.get_by_type_and_name tests
# ---------------------------------------------------------------------------


async def test_get_by_type_and_name_found(client, pool):
    """Returns a dict when the dimension exists."""
    svc = await create_service(client, "my-service")
    type_id = await _get_type_id(client, "service")

    dims = Dimensions(pool)
    result = await dims.get_by_type_and_name(type_id=type_id, name="my-service")

    assert_that(result).described_as("result is a dict").is_not_none()
    assert_that(str(result["id"])).described_as("id matches").is_equal_to(svc["id"])
    assert_that(result["name"]).described_as("name matches").is_equal_to("my-service")


async def test_get_by_type_and_name_not_found(client, pool):
    """Returns None when no dimension matches the type/name pair."""
    type_id = await _get_type_id(client, "service")

    dims = Dimensions(pool)
    result = await dims.get_by_type_and_name(type_id=type_id, name="nonexistent-xyz")

    assert_that(result).described_as("result is None").is_none()


async def test_get_by_type_and_name_wrong_type(client, pool):
    """Returns None when name exists but under a different type."""
    svc = await create_service(client, "cross-type-check")  # noqa: F841
    env_type_id = await _get_type_id(client, "environment")

    dims = Dimensions(pool)
    result = await dims.get_by_type_and_name(type_id=env_type_id, name="cross-type-check")

    assert_that(result).described_as("wrong type returns None").is_none()


# ---------------------------------------------------------------------------
# Configurations.get_for_rest_scope tests
# ---------------------------------------------------------------------------


async def test_get_for_rest_scope_single_matching_config(client, pool):
    """Returns the one matching config with its substitutions embedded."""
    svc = await create_service(client, "scope-svc")
    env = await create_environment(client, "scope-env")
    sv = await create_shared_value(client, "scope-secret")

    await create_configuration(
        client,
        [svc["id"], env["id"]],
        {"host": "_"},
        [{"jsonpath": "$.host", "sharedValueId": sv["id"]}],
    )

    configs = Configurations(pool)
    results = await configs.get_for_rest_scope(dimension_ids=[svc["id"], env["id"]])

    assert_that(results).described_as("one config returned").is_length(1)
    cfg = results[0]
    assert_that(cfg).described_as("config has body").contains_key("body")
    assert_that(cfg).described_as("config has substitutions key").contains_key("substitutions")
    assert_that(cfg["substitutions"]).described_as("one substitution").is_length(1)
    assert_that(cfg["substitutions"][0]["jsonpath"]).described_as("substitution jsonpath").is_equal_to("$.host")


async def test_get_for_rest_scope_no_matching_configs(client, pool):
    """Returns an empty list when no current configs apply to the given scope."""
    svc = await create_service(client, "lonely-svc")
    env = await create_environment(client, "lonely-env")

    # Create a config scoped to a *different* service so it won't match
    other_svc = await create_service(client, "other-svc")
    await create_configuration(client, [other_svc["id"], env["id"]], {"other": True})

    configs = Configurations(pool)
    results = await configs.get_for_rest_scope(dimension_ids=[svc["id"], env["id"]])

    assert_that(results).described_as("no configs for unrelated scope").is_empty()


async def test_get_for_rest_scope_ordered_least_specific_first(client, pool):
    """Configs ordered by specificity: global (0 non-base dims) before specific (2)."""
    svc = await create_service(client, "order-svc")
    env = await create_environment(client, "order-env")

    # Global config (no non-base dims — assigned to base dims only)
    await create_configuration(client, [], {"specificity": "global"})
    # Specific config (two non-base dims)
    await create_configuration(client, [svc["id"], env["id"]], {"specificity": "specific"})

    configs = Configurations(pool)
    results = await configs.get_for_rest_scope(dimension_ids=[svc["id"], env["id"]])

    assert_that(results).described_as("two configs returned").is_length(2)
    specificities = [r["body"]["specificity"] for r in results]
    assert_that(specificities[0]).described_as("least specific (global) comes first").is_equal_to("global")
    assert_that(specificities[1]).described_as("most specific comes last").is_equal_to("specific")


async def test_get_for_rest_scope_substitutions_empty_when_none(client, pool):
    """Configs with no substitutions return an empty substitutions list."""
    svc = await create_service(client, "nosub-svc")
    env = await create_environment(client, "nosub-env")

    await create_configuration(client, [svc["id"], env["id"]], {"plain": True})

    configs = Configurations(pool)
    results = await configs.get_for_rest_scope(dimension_ids=[svc["id"], env["id"]])

    assert_that(results).described_as("one config returned").is_length(1)
    assert_that(results[0]["substitutions"]).described_as("substitutions list is empty").is_empty()
