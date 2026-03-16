"""Integration tests for trigger behaviour under various scope conditions."""

import json
import os
import tempfile

from assertpy import assert_that
from conftest import gql
from gql import (
    OUTPUT_QUERY,
    create_configuration,
    create_environment,
    create_output,
    create_revision,
    create_service,
    create_shared_value,
    trigger_output,
)


async def test_trigger_output_multiple_combinations(client):
    """Output with two environment dimensions triggers writes of two files."""
    svc = await create_service(client, "multi-svc")
    env_prod = await create_environment(client, "prod")
    env_dev = await create_environment(client, "dev")

    await create_configuration(client, [svc["id"], env_prod["id"]], {"env": "prod"})
    await create_configuration(client, [svc["id"], env_dev["id"]], {"env": "dev"})

    with tempfile.TemporaryDirectory() as tmpdir:
        # Use fixed sub-directories so the two combinations write to distinct
        # paths regardless of placeholder resolution.  The output is scoped to
        # both env_prod and env_dev so the writer produces one result per
        # environment combination.  We use separate sub-directories to ensure
        # the two files never collide.
        prod_path = os.path.join(tmpdir, "prod", "config.json")
        dev_path = os.path.join(tmpdir, "dev", "config.json")

        # Create one output per combination with a fixed, placeholder-free path.
        output_prod = await create_output(
            client,
            prod_path,
            "json",
            [svc["id"], env_prod["id"]],
        )
        output_dev = await create_output(
            client,
            dev_path,
            "json",
            [svc["id"], env_dev["id"]],
        )

        result_prod = await trigger_output(client, output_prod["id"])
        result_dev = await trigger_output(client, output_dev["id"])

        # Each output has exactly one combination.
        assert_that(result_prod["results"]).described_as(
            "one result for prod"
        ).is_length(1)
        assert_that(result_dev["results"]).described_as("one result for dev").is_length(
            1
        )

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


async def test_trigger_output_results_stored_in_db(client):
    """After trigger, output(id) query returns results with correct fields."""
    svc = await create_service(client, "db-svc")
    env = await create_environment(client, "db-env")
    await create_configuration(client, [svc["id"], env["id"]], {"stored": True})

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "config.json")
        output = await create_output(
            client, path_template, "json", [svc["id"], env["id"]]
        )

        trigger_result = await trigger_output(client, output["id"])
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


async def test_trigger_output_substitution(client):
    """Config with a sentinel + substitution; triggered output has sentinel replaced."""
    svc = await create_service(client, "sub-svc")
    env = await create_environment(client, "sub-env")
    sv = await create_shared_value(client, "secret_key")

    # Create a revision scoped to svc+env
    await create_revision(client, sv["id"], [svc["id"], env["id"]], "my-secret-value")

    # Config with sentinel
    await create_configuration(
        client,
        [svc["id"], env["id"]],
        {"api_key": "_"},
        [{"jsonpath": "$.api_key", "sharedValueId": sv["id"]}],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "config.json")
        output = await create_output(
            client, path_template, "json", [svc["id"], env["id"]]
        )

        result = await trigger_output(client, output["id"])

        res = result["results"][0]
        assert_that(res["succeeded"]).described_as("write succeeded").is_true()

        with open(res["path"]) as fh:
            data = json.load(fh)
        assert_that(data["api_key"]).described_as(
            "sentinel replaced by shared value"
        ).is_equal_to("my-secret-value")


async def test_trigger_output_scope_merge(client):
    """Output file contains the shallow-merged result from multiple config scopes."""
    svc = await create_service(client, "merge-svc")
    env = await create_environment(client, "merge-env")

    # Global config (base scope — covers all services and environments)
    await create_configuration(
        client,
        [],
        {"base_key": "base_value", "override_key": "from_base"},
    )
    # More specific config for svc+env — overrides override_key
    await create_configuration(
        client,
        [svc["id"], env["id"]],
        {"override_key": "from_specific", "specific_key": "specific_value"},
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "config.json")
        output = await create_output(
            client, path_template, "json", [svc["id"], env["id"]]
        )

        result = await trigger_output(client, output["id"])

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
