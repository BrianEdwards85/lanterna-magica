"""Integration tests for output error/edge-case and list-query behaviour."""

import os
import tempfile

from assertpy import assert_that
from conftest import gql
from gql import (
    ARCHIVE_OUTPUT,
    OUTPUTS_QUERY,
    TRIGGER_OUTPUT,
    create_configuration,
    create_environment,
    create_output,
    create_service,
    trigger_output,
)
from utils import nodes


async def test_trigger_output_no_configs_for_combination(client):
    """A combination with no configs yields succeeded: false; others succeed."""
    svc = await create_service(client, "combo-svc")
    env_has_config = await create_environment(client, "has-config")
    env_no_config = await create_environment(client, "no-config")

    # Only create a config for env_has_config
    await create_configuration(client, [svc["id"], env_has_config["id"]], {"env": "has-config"})

    with tempfile.TemporaryDirectory() as tmpdir:
        # Use two separate outputs with fixed placeholder-free paths so that
        # each combination writes to a distinct location.
        output_has = await create_output(
            client,
            os.path.join(tmpdir, "has-config.json"),
            "json",
            [svc["id"], env_has_config["id"]],
        )
        output_no = await create_output(
            client,
            os.path.join(tmpdir, "no-config.json"),
            "json",
            [svc["id"], env_no_config["id"]],
        )

        result_has = await trigger_output(client, output_has["id"])
        result_no = await trigger_output(client, output_no["id"])

        assert_that(result_has["results"]).described_as("one result for has-config output").is_length(1)
        assert_that(result_no["results"]).described_as("one result for no-config output").is_length(1)

        succeeded_results = [
            r for results in (result_has["results"], result_no["results"]) for r in results if r["succeeded"]
        ]
        failed_results = [
            r for results in (result_has["results"], result_no["results"]) for r in results if not r["succeeded"]
        ]

        assert_that(succeeded_results).described_as("one success").is_length(1)
        assert_that(failed_results).described_as("one failure").is_length(1)

        failed_res = failed_results[0]
        assert_that(failed_res["error"]).described_as("error message present").is_not_none()
        assert_that(failed_res["error"]).described_as("error is non-empty").is_not_empty()


async def test_trigger_output_oserror_on_write(client):
    """Output path template pointing to unwritable location produces failed result."""
    svc = await create_service(client, "oserr-svc")
    env = await create_environment(client, "oserr-env")
    await create_configuration(client, [svc["id"], env["id"]], {"key": "value"})

    # /proc/nope/ cannot be created
    path_template = "/proc/nope/{service}.json"
    output = await create_output(client, path_template, "json", [svc["id"], env["id"]])

    result = await trigger_output(client, output["id"])

    assert_that(result["results"]).described_as("one result").is_length(1)
    res = result["results"][0]
    assert_that(res["succeeded"]).described_as("write failed").is_false()
    assert_that(res["error"]).described_as("error message is set").is_not_none()
    assert_that(res["error"]).described_as("error is non-empty").is_not_empty()


async def test_trigger_archived_output_returns_error(client):
    """Triggering an archived output returns a GraphQL error."""
    svc = await create_service(client, "arch-svc")
    env = await create_environment(client, "arch-env")
    await create_configuration(client, [svc["id"], env["id"]], {"key": "value"})

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "config.json")
        output = await create_output(client, path_template, "json", [svc["id"], env["id"]])

        # Archive the output
        await gql(client, ARCHIVE_OUTPUT, {"id": output["id"]})

        # Triggering an archived output must return an error
        body = await gql(client, TRIGGER_OUTPUT, {"id": output["id"]}, expect_errors=True)
        assert_that(body).described_as("error returned").contains_key("errors")
        assert_that(body["errors"]).described_as("errors list not empty").is_not_empty()


async def test_outputs_list_query(client):
    """outputs query returns all active outputs."""
    svc = await create_service(client, "list-svc")
    env = await create_environment(client, "list-env")

    with tempfile.TemporaryDirectory() as tmpdir:
        out1 = await create_output(
            client,
            os.path.join(tmpdir, "a.json"),
            "json",
            [svc["id"], env["id"]],
        )
        out2 = await create_output(
            client,
            os.path.join(tmpdir, "b.json"),
            "json",
            [svc["id"], env["id"]],
        )

        body = await gql(client, OUTPUTS_QUERY)
        items = nodes(body["data"]["outputs"]["edges"])
        ids = [item["id"] for item in items]
        assert_that(ids).described_as("both outputs in list").contains(out1["id"], out2["id"])


async def test_outputs_list_excludes_archived_by_default(client):
    """outputs query excludes archived outputs when includeArchived is not set."""
    svc = await create_service(client, "arch-list-svc")
    env = await create_environment(client, "arch-list-env")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_active = await create_output(
            client,
            os.path.join(tmpdir, "active.json"),
            "json",
            [svc["id"], env["id"]],
        )
        out_archived = await create_output(
            client,
            os.path.join(tmpdir, "archived.json"),
            "json",
            [svc["id"], env["id"]],
        )
        await gql(client, ARCHIVE_OUTPUT, {"id": out_archived["id"]})

        body = await gql(client, OUTPUTS_QUERY)
        items = nodes(body["data"]["outputs"]["edges"])
        ids = [item["id"] for item in items]
        assert_that(ids).described_as("active output in list").contains(out_active["id"])
        assert_that(ids).described_as("archived output excluded").does_not_contain(out_archived["id"])


async def test_outputs_list_include_archived(client):
    """outputs query with includeArchived: true includes archived outputs."""
    svc = await create_service(client, "ia-svc")
    env = await create_environment(client, "ia-env")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_active = await create_output(
            client,
            os.path.join(tmpdir, "active2.json"),
            "json",
            [svc["id"], env["id"]],
        )
        out_archived = await create_output(
            client,
            os.path.join(tmpdir, "archived2.json"),
            "json",
            [svc["id"], env["id"]],
        )
        await gql(client, ARCHIVE_OUTPUT, {"id": out_archived["id"]})

        body = await gql(client, OUTPUTS_QUERY, {"includeArchived": True})
        items = nodes(body["data"]["outputs"]["edges"])
        ids = [item["id"] for item in items]
        assert_that(ids).described_as("both outputs shown with includeArchived").contains(
            out_active["id"], out_archived["id"]
        )
