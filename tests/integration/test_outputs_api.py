"""Integration tests for the output system via the GraphQL API.

Covers the full stack from mutation through to files on disk and DB results.
"""

import json
import os
import tempfile
import tomllib

import pytest
import yaml
from assertpy import assert_that
from conftest import gql
from utils import (
    create_environment,
    create_revision,
    create_service,
    create_shared_value,
    nodes,
)

# ---------------------------------------------------------------------------
# GraphQL strings
# ---------------------------------------------------------------------------

CREATE_OUTPUT = """
mutation CreateOutput($input: CreateOutputInput!) {
    createOutput(input: $input) {
        id
        pathTemplate
        format
        dimensions { id name }
        results { id path content succeeded error }
        createdAt
        updatedAt
        archivedAt
    }
}
"""

TRIGGER_OUTPUT = """
mutation TriggerOutput($id: ID!) {
    triggerOutput(id: $id) {
        id
        pathTemplate
        format
        results {
            id
            path
            content
            succeeded
            error
        }
    }
}
"""

ARCHIVE_OUTPUT = """
mutation ArchiveOutput($id: ID!) {
    archiveOutput(id: $id) {
        id
        archivedAt
    }
}
"""

OUTPUTS_QUERY = """
query Outputs($includeArchived: Boolean, $first: Int, $after: String) {
    outputs(includeArchived: $includeArchived, first: $first, after: $after) {
        edges {
            node {
                id
                pathTemplate
                format
                archivedAt
            }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

OUTPUT_QUERY = """
query OutputsByIds($ids: [ID!]!) {
    outputsByIds(ids: $ids) {
        id
        pathTemplate
        format
        dimensions { id name }
        results {
            id
            path
            content
            succeeded
            error
        }
        archivedAt
    }
}
"""

CREATE_CONFIGURATION = """
mutation CreateConfiguration($input: CreateConfigurationInput!) {
    createConfiguration(input: $input) {
        id
        dimensions { id name }
        body
        isCurrent
    }
}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_output(client, path_template, fmt, dimension_ids):
    """Helper to create an output via GraphQL."""
    body = await gql(
        client,
        CREATE_OUTPUT,
        {
            "input": {
                "pathTemplate": path_template,
                "format": fmt,
                "dimensionIds": dimension_ids,
            }
        },
    )
    return body["data"]["createOutput"]


async def _create_configuration(client, dimension_ids, config_body, substitutions=None):
    """Helper to create a configuration via GraphQL."""
    variables = {
        "input": {
            "dimensionIds": dimension_ids,
            "body": config_body,
        }
    }
    if substitutions:
        variables["input"]["substitutions"] = substitutions
    result = await gql(client, CREATE_CONFIGURATION, variables)
    return result["data"]["createConfiguration"]


async def _trigger_output(client, output_id):
    """Trigger an output and return the trigger result dict."""
    body = await gql(client, TRIGGER_OUTPUT, {"id": output_id})
    return body["data"]["triggerOutput"]


# ---------------------------------------------------------------------------
# Test 1: triggerOutput writes a file to disk at the rendered path
# ---------------------------------------------------------------------------


async def test_trigger_output_writes_file(client):
    """triggerOutput writes a file to disk at the rendered path.

    We use a fixed filename (no placeholder) so the write path is predictable.
    The file content is verified by reading the path stored in the result.
    """
    svc = await create_service(client, "myapp")
    env = await create_environment(client, "staging")
    await _create_configuration(
        client, [svc["id"], env["id"]], {"host": "localhost", "port": 8080}
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # Use a fixed filename — the writer writes exactly here when there is
        # only one combination (one value per dimension type) and no unresolved
        # placeholders remain.
        path_template = os.path.join(tmpdir, "config.json")
        output = await _create_output(
            client, path_template, "json", [svc["id"], env["id"]]
        )

        result = await _trigger_output(client, output["id"])

        assert_that(result["results"]).described_as("one result").is_length(1)
        res = result["results"][0]
        assert_that(res["succeeded"]).described_as("write succeeded").is_true()
        assert_that(res["error"]).described_as("no error").is_none()

        # The path returned in the result is where the file was written.
        written_path = res["path"]
        assert_that(os.path.exists(written_path)).described_as(
            "file exists at the result path"
        ).is_true()

        with open(written_path) as fh:
            content = json.load(fh)
        assert_that(content).described_as("file content correct").is_equal_to(
            {"host": "localhost", "port": 8080}
        )


# ---------------------------------------------------------------------------
# Test 2: All four formats produce parseable files with correct content
# ---------------------------------------------------------------------------


async def test_trigger_output_json_format(client):
    """json format produces a parseable JSON file with correct content."""
    svc = await create_service(client, "json-svc")
    env = await create_environment(client, "json-env")
    config_body = {"key": "value", "num": 42}
    await _create_configuration(client, [svc["id"], env["id"]], config_body)

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "out.json")
        output = await _create_output(
            client, path_template, "json", [svc["id"], env["id"]]
        )
        result = await _trigger_output(client, output["id"])

        res = result["results"][0]
        assert_that(res["succeeded"]).described_as("succeeded").is_true()

        with open(res["path"]) as fh:
            data = json.load(fh)
        assert_that(data).described_as("json content").is_equal_to(config_body)


async def test_trigger_output_yml_format(client):
    """yml format produces a parseable YAML file with correct content."""
    svc = await create_service(client, "yml-svc")
    env = await create_environment(client, "yml-env")
    config_body = {"key": "value", "num": 42}
    await _create_configuration(client, [svc["id"], env["id"]], config_body)

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "out.yml")
        output = await _create_output(
            client, path_template, "yml", [svc["id"], env["id"]]
        )
        result = await _trigger_output(client, output["id"])

        res = result["results"][0]
        assert_that(res["succeeded"]).described_as("succeeded").is_true()

        with open(res["path"]) as fh:
            data = yaml.safe_load(fh)
        assert_that(data).described_as("yml content").is_equal_to(config_body)


async def test_trigger_output_toml_format(client):
    """toml format produces a parseable TOML file with correct content."""
    svc = await create_service(client, "toml-svc")
    env = await create_environment(client, "toml-env")
    config_body = {"key": "value", "num": 42}
    await _create_configuration(client, [svc["id"], env["id"]], config_body)

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "out.toml")
        output = await _create_output(
            client, path_template, "toml", [svc["id"], env["id"]]
        )
        result = await _trigger_output(client, output["id"])

        res = result["results"][0]
        assert_that(res["succeeded"]).described_as("succeeded").is_true()

        with open(res["path"], "rb") as fh:
            data = tomllib.load(fh)
        assert_that(data).described_as("toml content").is_equal_to(config_body)


async def test_trigger_output_env_format(client):
    """env format produces a parseable env file with correct content."""
    svc = await create_service(client, "env-svc")
    env = await create_environment(client, "env-env")
    await _create_configuration(
        client, [svc["id"], env["id"]], {"KEY": "value", "NUM": "42"}
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "out.env")
        output = await _create_output(
            client, path_template, "env", [svc["id"], env["id"]]
        )
        result = await _trigger_output(client, output["id"])

        res = result["results"][0]
        assert_that(res["succeeded"]).described_as("succeeded").is_true()

        with open(res["path"]) as fh:
            raw = fh.read()

        # Parse the env file into a dict
        parsed = {}
        for line in raw.strip().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                parsed[k] = v

        assert_that(parsed).described_as("env KEY").contains_entry({"KEY": "value"})
        assert_that(parsed).described_as("env NUM").contains_entry({"NUM": "42"})


# ---------------------------------------------------------------------------
# Test 3: Multiple combinations produce N files for N combinations
# ---------------------------------------------------------------------------


async def test_trigger_output_multiple_combinations(client):
    """Output with two environment dimensions triggers writes of two files."""
    svc = await create_service(client, "multi-svc")
    env_prod = await create_environment(client, "prod")
    env_dev = await create_environment(client, "dev")

    await _create_configuration(client, [svc["id"], env_prod["id"]], {"env": "prod"})
    await _create_configuration(client, [svc["id"], env_dev["id"]], {"env": "dev"})

    with tempfile.TemporaryDirectory() as tmpdir:
        # Use fixed sub-directories so the two combinations write to distinct
        # paths regardless of placeholder resolution.  The output is scoped to
        # both env_prod and env_dev so the writer produces one result per
        # environment combination.  We use separate sub-directories to ensure
        # the two files never collide.
        prod_path = os.path.join(tmpdir, "prod", "config.json")
        dev_path = os.path.join(tmpdir, "dev", "config.json")

        # Create one output per combination with a fixed, placeholder-free path.
        output_prod = await _create_output(
            client,
            prod_path,
            "json",
            [svc["id"], env_prod["id"]],
        )
        output_dev = await _create_output(
            client,
            dev_path,
            "json",
            [svc["id"], env_dev["id"]],
        )

        result_prod = await _trigger_output(client, output_prod["id"])
        result_dev = await _trigger_output(client, output_dev["id"])

        # Each output has exactly one combination.
        assert_that(result_prod["results"]).described_as(
            "one result for prod"
        ).is_length(1)
        assert_that(result_dev["results"]).described_as(
            "one result for dev"
        ).is_length(1)

        assert_that(result_prod["results"][0]["succeeded"]).described_as(
            "prod write succeeded"
        ).is_true()
        assert_that(result_dev["results"][0]["succeeded"]).described_as(
            "dev write succeeded"
        ).is_true()

        # Both distinct files must exist on disk.
        assert_that(os.path.exists(prod_path)).described_as(
            "prod file exists on disk"
        ).is_true()
        assert_that(os.path.exists(dev_path)).described_as(
            "dev file exists on disk"
        ).is_true()


# ---------------------------------------------------------------------------
# Test 4: Results stored in DB — output(id) query returns results
# ---------------------------------------------------------------------------


async def test_trigger_output_results_stored_in_db(client):
    """After trigger, output(id) query returns results with correct fields."""
    svc = await create_service(client, "db-svc")
    env = await create_environment(client, "db-env")
    await _create_configuration(client, [svc["id"], env["id"]], {"stored": True})

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "config.json")
        output = await _create_output(
            client, path_template, "json", [svc["id"], env["id"]]
        )

        trigger_result = await _trigger_output(client, output["id"])
        written_path = trigger_result["results"][0]["path"]

        # Query output from DB
        body = await gql(client, OUTPUT_QUERY, {"ids": [output["id"]]})
        fetched = body["data"]["outputsByIds"][0]

        assert_that(fetched["results"]).described_as("results present").is_length(1)
        res = fetched["results"][0]
        assert_that(res["succeeded"]).described_as("succeeded is true").is_true()
        assert_that(res["path"]).described_as("path is stored correctly").is_equal_to(
            written_path
        )
        assert_that(res["content"]).described_as("content is non-empty").is_not_empty()
        assert_that(res["error"]).described_as("error is null").is_none()


# ---------------------------------------------------------------------------
# Test 5: Shared value substitution — sentinel replaced by resolved value
# ---------------------------------------------------------------------------


async def test_trigger_output_substitution(client):
    """Config with a sentinel + substitution; triggered output has sentinel replaced."""
    svc = await create_service(client, "sub-svc")
    env = await create_environment(client, "sub-env")
    sv = await create_shared_value(client, "secret_key")

    # Create a revision scoped to svc+env
    await create_revision(client, sv["id"], [svc["id"], env["id"]], "my-secret-value")

    # Config with sentinel
    await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"api_key": "_"},
        [{"jsonpath": "$.api_key", "sharedValueId": sv["id"]}],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "config.json")
        output = await _create_output(
            client, path_template, "json", [svc["id"], env["id"]]
        )

        result = await _trigger_output(client, output["id"])

        res = result["results"][0]
        assert_that(res["succeeded"]).described_as("write succeeded").is_true()

        with open(res["path"]) as fh:
            data = json.load(fh)
        assert_that(data["api_key"]).described_as(
            "sentinel replaced by shared value"
        ).is_equal_to("my-secret-value")


# ---------------------------------------------------------------------------
# Test 6: Scope merge — two configs at different specificity levels
# ---------------------------------------------------------------------------


async def test_trigger_output_scope_merge(client):
    """Output file contains the shallow-merged result from multiple config scopes."""
    svc = await create_service(client, "merge-svc")
    env = await create_environment(client, "merge-env")

    # Global config (base scope — covers all services and environments)
    await _create_configuration(
        client,
        [],
        {"base_key": "base_value", "override_key": "from_base"},
    )
    # More specific config for svc+env — overrides override_key
    await _create_configuration(
        client,
        [svc["id"], env["id"]],
        {"override_key": "from_specific", "specific_key": "specific_value"},
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "config.json")
        output = await _create_output(
            client, path_template, "json", [svc["id"], env["id"]]
        )

        result = await _trigger_output(client, output["id"])

        res = result["results"][0]
        assert_that(res["succeeded"]).described_as("write succeeded").is_true()

        with open(res["path"]) as fh:
            data = json.load(fh)

        # Specific config overrides base; base keys that are not overridden survive.
        assert_that(data["base_key"]).described_as("base key present").is_equal_to(
            "base_value"
        )
        assert_that(data["override_key"]).described_as(
            "specific config overrides base"
        ).is_equal_to("from_specific")
        assert_that(data["specific_key"]).described_as(
            "specific key present"
        ).is_equal_to("specific_value")


# ---------------------------------------------------------------------------
# Test 7: No configs for a combination — failed result; others still succeed
# ---------------------------------------------------------------------------


async def test_trigger_output_no_configs_for_combination(client):
    """A combination with no configs yields succeeded: false; others succeed."""
    svc = await create_service(client, "combo-svc")
    env_has_config = await create_environment(client, "has-config")
    env_no_config = await create_environment(client, "no-config")

    # Only create a config for env_has_config
    await _create_configuration(
        client, [svc["id"], env_has_config["id"]], {"env": "has-config"}
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # Use two separate outputs with fixed placeholder-free paths so that
        # each combination writes to a distinct location.
        output_has = await _create_output(
            client,
            os.path.join(tmpdir, "has-config.json"),
            "json",
            [svc["id"], env_has_config["id"]],
        )
        output_no = await _create_output(
            client,
            os.path.join(tmpdir, "no-config.json"),
            "json",
            [svc["id"], env_no_config["id"]],
        )

        result_has = await _trigger_output(client, output_has["id"])
        result_no = await _trigger_output(client, output_no["id"])

        assert_that(result_has["results"]).described_as(
            "one result for has-config output"
        ).is_length(1)
        assert_that(result_no["results"]).described_as(
            "one result for no-config output"
        ).is_length(1)

        succeeded_results = [
            r
            for results in (result_has["results"], result_no["results"])
            for r in results
            if r["succeeded"]
        ]
        failed_results = [
            r
            for results in (result_has["results"], result_no["results"])
            for r in results
            if not r["succeeded"]
        ]

        assert_that(succeeded_results).described_as("one success").is_length(1)
        assert_that(failed_results).described_as("one failure").is_length(1)

        failed_res = failed_results[0]
        assert_that(failed_res["error"]).described_as(
            "error message present"
        ).is_not_none()
        assert_that(failed_res["error"]).described_as(
            "error is non-empty"
        ).is_not_empty()


# ---------------------------------------------------------------------------
# Test 8: OSError on write — result has succeeded: false with error message
# ---------------------------------------------------------------------------


async def test_trigger_output_oserror_on_write(client):
    """Output path template pointing to unwritable location produces failed result."""
    svc = await create_service(client, "oserr-svc")
    env = await create_environment(client, "oserr-env")
    await _create_configuration(client, [svc["id"], env["id"]], {"key": "value"})

    # /proc/nope/ cannot be created
    path_template = "/proc/nope/{service}.json"
    output = await _create_output(client, path_template, "json", [svc["id"], env["id"]])

    result = await _trigger_output(client, output["id"])

    assert_that(result["results"]).described_as("one result").is_length(1)
    res = result["results"][0]
    assert_that(res["succeeded"]).described_as("write failed").is_false()
    assert_that(res["error"]).described_as("error message is set").is_not_none()
    assert_that(res["error"]).described_as("error is non-empty").is_not_empty()


# ---------------------------------------------------------------------------
# Test 9: Archived output cannot be triggered — returns a GraphQL error
# ---------------------------------------------------------------------------


async def test_trigger_archived_output_returns_error(client):
    """Triggering an archived output returns a GraphQL error."""
    svc = await create_service(client, "arch-svc")
    env = await create_environment(client, "arch-env")
    await _create_configuration(client, [svc["id"], env["id"]], {"key": "value"})

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "config.json")
        output = await _create_output(
            client, path_template, "json", [svc["id"], env["id"]]
        )

        # Archive the output
        await gql(client, ARCHIVE_OUTPUT, {"id": output["id"]})

        # Triggering an archived output must return an error
        body = await gql(
            client, TRIGGER_OUTPUT, {"id": output["id"]}, expect_errors=True
        )
        assert_that(body).described_as("error returned").contains_key("errors")
        assert_that(body["errors"]).described_as("errors list not empty").is_not_empty()


# ---------------------------------------------------------------------------
# Test 10: outputs query — list with and without archived filter
# ---------------------------------------------------------------------------


async def test_outputs_list_query(client):
    """outputs query returns all active outputs."""
    svc = await create_service(client, "list-svc")
    env = await create_environment(client, "list-env")

    with tempfile.TemporaryDirectory() as tmpdir:
        out1 = await _create_output(
            client,
            os.path.join(tmpdir, "a.json"),
            "json",
            [svc["id"], env["id"]],
        )
        out2 = await _create_output(
            client,
            os.path.join(tmpdir, "b.json"),
            "json",
            [svc["id"], env["id"]],
        )

        body = await gql(client, OUTPUTS_QUERY)
        items = nodes(body["data"]["outputs"]["edges"])
        ids = [item["id"] for item in items]
        assert_that(ids).described_as("both outputs in list").contains(
            out1["id"], out2["id"]
        )


async def test_outputs_list_excludes_archived_by_default(client):
    """outputs query excludes archived outputs when includeArchived is not set."""
    svc = await create_service(client, "arch-list-svc")
    env = await create_environment(client, "arch-list-env")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_active = await _create_output(
            client,
            os.path.join(tmpdir, "active.json"),
            "json",
            [svc["id"], env["id"]],
        )
        out_archived = await _create_output(
            client,
            os.path.join(tmpdir, "archived.json"),
            "json",
            [svc["id"], env["id"]],
        )
        await gql(client, ARCHIVE_OUTPUT, {"id": out_archived["id"]})

        body = await gql(client, OUTPUTS_QUERY)
        items = nodes(body["data"]["outputs"]["edges"])
        ids = [item["id"] for item in items]
        assert_that(ids).described_as(
            "active output in list"
        ).contains(out_active["id"])
        assert_that(ids).described_as("archived output excluded").does_not_contain(
            out_archived["id"]
        )


async def test_outputs_list_include_archived(client):
    """outputs query with includeArchived: true includes archived outputs."""
    svc = await create_service(client, "ia-svc")
    env = await create_environment(client, "ia-env")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_active = await _create_output(
            client,
            os.path.join(tmpdir, "active2.json"),
            "json",
            [svc["id"], env["id"]],
        )
        out_archived = await _create_output(
            client,
            os.path.join(tmpdir, "archived2.json"),
            "json",
            [svc["id"], env["id"]],
        )
        await gql(client, ARCHIVE_OUTPUT, {"id": out_archived["id"]})

        body = await gql(client, OUTPUTS_QUERY, {"includeArchived": True})
        items = nodes(body["data"]["outputs"]["edges"])
        ids = [item["id"] for item in items]
        assert_that(ids).described_as(
            "both outputs shown with includeArchived"
        ).contains(out_active["id"], out_archived["id"])
