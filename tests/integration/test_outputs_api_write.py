"""Integration tests for output file-write and format correctness."""

import json
import os
import tempfile
import tomllib

import yaml
from assertpy import assert_that
from gql import (
    create_configuration,
    create_environment,
    create_output,
    create_service,
    trigger_output,
)


async def test_trigger_output_writes_file(client):
    """triggerOutput writes a file to disk at the rendered path.

    We use a fixed filename (no placeholder) so the write path is predictable.
    The file content is verified by reading the path stored in the result.
    """
    svc = await create_service(client, "myapp")
    env = await create_environment(client, "staging")
    await create_configuration(client, [svc["id"], env["id"]], {"host": "localhost", "port": 8080})

    with tempfile.TemporaryDirectory() as tmpdir:
        # Use a fixed filename — the writer writes exactly here when there is
        # only one combination (one value per dimension type) and no unresolved
        # placeholders remain.
        path_template = os.path.join(tmpdir, "config.json")
        output = await create_output(client, path_template, "json", [svc["id"], env["id"]])

        result = await trigger_output(client, output["id"])

        assert_that(result["results"]).described_as("one result").is_length(1)
        res = result["results"][0]
        assert_that(res["succeeded"]).described_as("write succeeded").is_true()
        assert_that(res["error"]).described_as("no error").is_none()

        # The path returned in the result is where the file was written.
        written_path = res["path"]
        assert_that(os.path.exists(written_path)).described_as("file exists at the result path").is_true()

        with open(written_path) as fh:
            content = json.load(fh)
        assert_that(content).described_as("file content correct").is_equal_to({"host": "localhost", "port": 8080})


async def test_trigger_output_json_format(client):
    """json format produces a parseable JSON file with correct content."""
    svc = await create_service(client, "json-svc")
    env = await create_environment(client, "json-env")
    config_body = {"key": "value", "num": 42}
    await create_configuration(client, [svc["id"], env["id"]], config_body)

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "out.json")
        output = await create_output(client, path_template, "json", [svc["id"], env["id"]])
        result = await trigger_output(client, output["id"])

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
    await create_configuration(client, [svc["id"], env["id"]], config_body)

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "out.yml")
        output = await create_output(client, path_template, "yml", [svc["id"], env["id"]])
        result = await trigger_output(client, output["id"])

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
    await create_configuration(client, [svc["id"], env["id"]], config_body)

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "out.toml")
        output = await create_output(client, path_template, "toml", [svc["id"], env["id"]])
        result = await trigger_output(client, output["id"])

        res = result["results"][0]
        assert_that(res["succeeded"]).described_as("succeeded").is_true()

        with open(res["path"], "rb") as fh:
            data = tomllib.load(fh)
        assert_that(data).described_as("toml content").is_equal_to(config_body)


async def test_trigger_output_env_format(client):
    """env format produces a parseable env file with correct content."""
    svc = await create_service(client, "env-svc")
    env = await create_environment(client, "env-env")
    await create_configuration(client, [svc["id"], env["id"]], {"KEY": "value", "NUM": "42"})

    with tempfile.TemporaryDirectory() as tmpdir:
        path_template = os.path.join(tmpdir, "out.env")
        output = await create_output(client, path_template, "env", [svc["id"], env["id"]])
        result = await trigger_output(client, output["id"])

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
