"""Integration tests for the GET /config/{slug} REST endpoint.

Covers JSON/YAML/TOML serialization, scope merging, query-param dimensions,
shared value substitution, and 404/400 error cases.
"""

import tomllib

import yaml
from assertpy import assert_that
from gql import (
    create_configuration,
    create_environment,
    create_revision,
    create_service,
    create_shared_value,
)

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


async def test_json_format_200(client):
    """GET /config/{name}.json returns 200 with application/json and correct body."""
    svc = await create_service(client, "json-svc")
    env = await create_environment(client, "json-env")
    config_body = {"host": "localhost", "port": 8080}
    await create_configuration(client, [svc["id"], env["id"]], config_body)

    resp = await client.get("/config/json-svc.json?environment=json-env")

    assert_that(resp.status_code).described_as("status code").is_equal_to(200)
    assert_that(resp.headers["content-type"]).described_as("content-type").contains(
        "application/json"
    )
    assert_that(resp.json()).described_as("response body").is_equal_to(config_body)


async def test_yaml_format_200(client):
    """GET /config/{name}.yml returns 200 with text/yaml and correct body."""
    svc = await create_service(client, "yaml-svc")
    env = await create_environment(client, "yaml-env")
    config_body = {"host": "yaml-host", "port": 9090}
    await create_configuration(client, [svc["id"], env["id"]], config_body)

    resp = await client.get("/config/yaml-svc.yml?environment=yaml-env")

    assert_that(resp.status_code).described_as("status code").is_equal_to(200)
    assert_that(resp.headers["content-type"]).described_as("content-type").contains(
        "text/yaml"
    )
    parsed = yaml.safe_load(resp.text)
    assert_that(parsed).described_as("parsed YAML body").is_equal_to(config_body)


async def test_toml_format_200(client):
    """GET /config/{name}.toml returns 200 with application/toml and correct body."""
    svc = await create_service(client, "toml-svc")
    env = await create_environment(client, "toml-env")
    config_body = {"host": "toml-host", "port": 7070}
    await create_configuration(client, [svc["id"], env["id"]], config_body)

    resp = await client.get("/config/toml-svc.toml?environment=toml-env")

    assert_that(resp.status_code).described_as("status code").is_equal_to(200)
    assert_that(resp.headers["content-type"]).described_as("content-type").contains(
        "application/toml"
    )
    parsed = tomllib.loads(resp.text)
    assert_that(parsed).described_as("parsed TOML body").is_equal_to(config_body)


async def test_scope_merge(client):
    """Most-specific config's keys overwrite base keys; unique keys from both are kept."""
    svc = await create_service(client, "merge-svc")

    # Global config (no specific dims — assigned to base dims only)
    await create_configuration(client, [], {"a": 1, "b": 2})
    # Service-specific config overrides 'b' and adds 'c'
    await create_configuration(client, [svc["id"]], {"b": 99, "c": 3})

    resp = await client.get("/config/merge-svc.json")

    assert_that(resp.status_code).described_as("status code").is_equal_to(200)
    body = resp.json()
    assert_that(body).described_as("merged 'a' from global").has_a(1)
    assert_that(body).described_as("merged 'b' overwritten by specific").has_b(99)
    assert_that(body).described_as("merged 'c' from specific").has_c(3)


async def test_query_param_dimension(client):
    """Config scoped to a specific environment is found when ?environment= is passed."""
    svc = await create_service(client, "qp-svc")
    prod = await create_environment(client, "prod")
    config_body = {"env": "prod-only"}
    await create_configuration(client, [svc["id"], prod["id"]], config_body)

    resp = await client.get("/config/qp-svc.json?environment=prod")

    assert_that(resp.status_code).described_as("status code").is_equal_to(200)
    assert_that(resp.json()).described_as("response body").is_equal_to(config_body)


async def test_shared_value_substitution(client):
    """Sentinel '_' is replaced by the resolved shared value in the response."""
    svc = await create_service(client, "sub-svc")
    env = await create_environment(client, "sub-env")
    sv = await create_shared_value(client, "db_password")

    # Create a revision for this shared value scoped to svc+env
    await create_revision(client, sv["id"], [svc["id"], env["id"]], "s3cr3t")

    config_body = {"database": {"password": "_"}}
    await create_configuration(
        client,
        [svc["id"], env["id"]],
        config_body,
        [{"jsonpath": "$.database.password", "sharedValueId": sv["id"]}],
    )

    resp = await client.get("/config/sub-svc.json?environment=sub-env")

    assert_that(resp.status_code).described_as("status code").is_equal_to(200)
    body = resp.json()
    assert_that(body["database"]["password"]).described_as(
        "sentinel replaced by shared value"
    ).is_equal_to("s3cr3t")


async def test_404_unknown_slug(client):
    """GET /config/nonexistent.json returns 404 when no such service dimension exists."""
    resp = await client.get("/config/nonexistent-xyz-service.json")

    assert_that(resp.status_code).described_as("status code").is_equal_to(404)


async def test_404_unknown_query_param_value(client):
    """GET /config/traefik.json?environment=nonexistent returns 404."""
    svc = await create_service(client, "traefik-qp")
    await create_configuration(client, [svc["id"]], {"key": "value"})

    resp = await client.get("/config/traefik-qp.json?environment=nonexistent-env-xyz")

    assert_that(resp.status_code).described_as("status code").is_equal_to(404)


async def test_404_no_configs_for_scope(client):
    """Returns 404 when a service dimension exists but has no matching configs."""
    # Create the service dimension but no configs for it
    svc = await create_service(client, "empty-svc")  # noqa: F841

    resp = await client.get("/config/empty-svc.json")

    assert_that(resp.status_code).described_as("status code").is_equal_to(404)


async def test_400_unknown_format(client):
    """GET /config/{name}.xyz returns 400 for unrecognised format extension."""
    svc = await create_service(client, "fmt-svc")
    await create_configuration(client, [svc["id"]], {"key": "value"})

    resp = await client.get("/config/fmt-svc.xyz")

    assert_that(resp.status_code).described_as("status code").is_equal_to(400)
    detail = resp.json()
    assert_that(detail).described_as("error response has detail key").contains_key(
        "detail"
    )


async def test_400_no_dot_in_slug(client):
    """GET /config/nodotslug (no '.' in path) returns 400 with a detail key."""
    resp = await client.get("/config/nodotslug")

    assert_that(resp.status_code).described_as("status code").is_equal_to(400)
    detail = resp.json()
    assert_that(detail).described_as("error response has detail key").contains_key(
        "detail"
    )


async def test_scope_merge_with_query_param_dimension(client):
    """Merges global base config with service+environment config via query param.

    The more-specific config's keys overwrite base keys; unique keys from the
    base config are preserved.  Exercises the full merge + query-param
    dimension resolution path together.
    """
    svc = await create_service(client, "myapp")
    env = await create_environment(client, "prod")

    # Global base config (no dimensions — applies to all scopes)
    await create_configuration(client, [], {"log_level": "info", "timeout": 30})
    # Service+environment-scoped config overrides only log_level
    await create_configuration(client, [svc["id"], env["id"]], {"log_level": "debug"})

    resp = await client.get("/config/myapp.json?environment=prod")

    assert_that(resp.status_code).described_as("status code").is_equal_to(200)
    body = resp.json()
    assert_that(body).described_as("merged result").is_equal_to(
        {"log_level": "debug", "timeout": 30}
    )
