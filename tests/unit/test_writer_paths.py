"""Unit tests for OutputWriter - path rendering and serialization."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from helpers import _make_dim, _make_output, _make_writer

from lanterna_magica.writer.outputs import _render_path

# ---------------------------------------------------------------------------
# Path rendering
# ---------------------------------------------------------------------------


def test_render_path_replaces_type_name_placeholders():
    combination = {
        "type-env": _make_dim("env-prod", "type-env", "prod"),
        "type-svc": _make_dim("svc-api", "type-svc", "api"),
    }
    type_id_to_name = {"type-env": "environment", "type-svc": "service"}
    path = _render_path(
        "/etc/{environment}/{service}.json", combination, type_id_to_name
    )
    assert path == "/etc/prod/api.json"


def test_render_path_falls_back_to_type_id_when_name_missing():
    combination = {
        "type-env": _make_dim("env-prod", "type-env", "prod"),
    }
    # No type_id_to_name mapping provided
    path = _render_path("/{type-env}.json", combination, {})
    assert path == "/prod.json"


def test_render_path_no_combination_returns_template_unchanged():
    path = _render_path("/etc/global.json", {}, {})
    assert path == "/etc/global.json"


@pytest.mark.asyncio
async def test_write_path_rendered_correctly_in_upsert():
    output = _make_output(path_template="/cfg/{env}/{svc}.json", fmt="json")
    dimensions = [
        _make_dim("env-prod", "type-env", "prod"),
        _make_dim("svc-api", "type-svc", "api"),
    ]
    dimension_types = [
        {"id": "type-env", "name": "env"},
        {"id": "type-svc", "name": "svc"},
    ]

    upsert_calls = []

    async def fake_upsert(**kwargs):
        upsert_calls.append(kwargs)
        return {"succeeded": True}

    writer = _make_writer(
        output=output, dimensions=dimensions, dimension_types=dimension_types
    )
    writer._outputs.upsert_result = fake_upsert

    with patch("builtins.open", MagicMock()), patch("os.makedirs"):
        await writer.write(output_id="out-1")

    assert len(upsert_calls) == 1
    assert upsert_calls[0]["path"] == "/cfg/prod/api.json"


# ---------------------------------------------------------------------------
# Serialization formats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_calls_serialize_with_correct_format():
    for fmt in ("json", "yml", "toml", "env"):
        path_tmpl = "/cfg/out." + fmt
        output = _make_output(path_template=path_tmpl, fmt=fmt)
        dimensions = [_make_dim("env-prod", "type-env", "prod")]
        dimension_types = [{"id": "type-env", "name": "env"}]

        writer = _make_writer(
            output=output, dimensions=dimensions, dimension_types=dimension_types
        )
        writer._outputs.upsert_result = AsyncMock(return_value={"succeeded": True})

        with patch("builtins.open", MagicMock()), patch("os.makedirs"):
            await writer.write(output_id="out-1")

        writer._orchestrator.serialize.assert_called_with(
            writer._orchestrator.resolve_scope.return_value, fmt
        )


# ---------------------------------------------------------------------------
# upsert_result called for every combination (success and failure)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_result_called_for_every_combination():
    output = _make_output(path_template="/cfg/{env}/{svc}.json", fmt="json")
    dimensions = [
        _make_dim("env-prod", "type-env", "prod"),
        _make_dim("env-staging", "type-env", "staging"),
        _make_dim("svc-api", "type-svc", "api"),
        _make_dim("svc-worker", "type-svc", "worker"),
    ]
    dimension_types = [
        {"id": "type-env", "name": "env"},
        {"id": "type-svc", "name": "svc"},
    ]

    upsert_calls = []

    async def fake_upsert(**kwargs):
        upsert_calls.append(kwargs)
        return {"succeeded": True}

    writer = _make_writer(
        output=output, dimensions=dimensions, dimension_types=dimension_types
    )
    writer._outputs.upsert_result = fake_upsert

    with patch("builtins.open", MagicMock()), patch("os.makedirs"):
        results = await writer.write(output_id="out-1")

    # 2 environments x 2 services = 4 combinations
    assert len(upsert_calls) == 4
    assert len(results) == 4


# ---------------------------------------------------------------------------
# makedirs called before each file write
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_makedirs_called_before_each_write():
    output = _make_output(path_template="/cfg/{env}/{svc}.json", fmt="json")
    dimensions = [
        _make_dim("env-prod", "type-env", "prod"),
        _make_dim("svc-api", "type-svc", "api"),
    ]
    dimension_types = [
        {"id": "type-env", "name": "env"},
        {"id": "type-svc", "name": "svc"},
    ]

    writer = _make_writer(
        output=output, dimensions=dimensions, dimension_types=dimension_types
    )
    writer._outputs.upsert_result = AsyncMock(return_value={"succeeded": True})

    makedirs_calls = []

    def fake_makedirs(path, exist_ok=False):
        makedirs_calls.append((path, exist_ok))

    with patch("builtins.open", MagicMock()), patch("os.makedirs", fake_makedirs):
        await writer.write(output_id="out-1")

    assert len(makedirs_calls) == 1
    assert makedirs_calls[0] == ("/cfg/prod", True)
