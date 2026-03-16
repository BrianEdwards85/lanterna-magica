"""Unit tests for OutputWriter - NotFoundError and cartesian product logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from helpers import _make_dim, _make_output, _make_writer

from lanterna_magica.errors import NotFoundError

# ---------------------------------------------------------------------------
# NotFoundError cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_raises_not_found_when_output_missing():
    writer = _make_writer(output=None)
    with pytest.raises(NotFoundError):
        await writer.write(output_id="missing")


@pytest.mark.asyncio
async def test_write_raises_not_found_when_output_archived():
    output = _make_output(archived_at="2024-01-01T00:00:00")
    writer = _make_writer(output=output)
    with pytest.raises(NotFoundError):
        await writer.write(output_id="out-1")


# ---------------------------------------------------------------------------
# Cartesian product logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_two_types_two_values_each_produces_four_combinations():
    """2 types x 2 values each = 4 combinations."""
    output = _make_output(
        path_template="/cfg/{env}/{svc}.json",
        fmt="json",
    )
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
        return {"succeeded": True, **kwargs}

    writer = _make_writer(
        output=output, dimensions=dimensions, dimension_types=dimension_types
    )
    writer._outputs.upsert_result = fake_upsert

    with patch("builtins.open", MagicMock()), patch("os.makedirs"):
        results = await writer.write(output_id="out-1")

    assert len(results) == 4
    assert len(upsert_calls) == 4


@pytest.mark.asyncio
async def test_write_single_dimension_single_value_produces_one_combination():
    output = _make_output(path_template="/cfg/{env}.json", fmt="json")
    dimensions = [_make_dim("env-prod", "type-env", "prod")]
    dimension_types = [{"id": "type-env", "name": "env"}]

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

    assert len(results) == 1
    assert len(upsert_calls) == 1


@pytest.mark.asyncio
async def test_write_no_dimensions_produces_one_combination():
    """No dimensions → single global combination."""
    output = _make_output(path_template="/cfg/global.json", fmt="json")

    upsert_calls = []

    async def fake_upsert(**kwargs):
        upsert_calls.append(kwargs)
        return {"succeeded": True}

    writer = _make_writer(output=output, dimensions=[])
    writer._outputs.upsert_result = fake_upsert

    with patch("builtins.open", MagicMock()), patch("os.makedirs"):
        results = await writer.write(output_id="out-1")

    assert len(results) == 1
    assert len(upsert_calls) == 1
