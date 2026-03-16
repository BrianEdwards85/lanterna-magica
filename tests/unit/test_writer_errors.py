"""Unit tests for OutputWriter - OSError and ValueError handling."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from helpers import _make_dim, _make_output, _make_writer

# ---------------------------------------------------------------------------
# OSError handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_oserror_records_failed_result_and_continues():
    """OSError on file write is caught; remaining combinations continue."""
    output = _make_output(path_template="/cfg/{env}.json", fmt="json")
    dimensions = [
        _make_dim("env-prod", "type-env", "prod"),
        _make_dim("env-staging", "type-env", "staging"),
    ]
    dimension_types = [{"id": "type-env", "name": "env"}]

    upsert_calls = []

    async def fake_upsert(**kwargs):
        upsert_calls.append(kwargs)
        return {**kwargs}

    writer = _make_writer(output=output, dimensions=dimensions, dimension_types=dimension_types)
    writer._outputs.upsert_result = fake_upsert

    # First open raises OSError, second succeeds.
    open_calls = []

    def fake_open(path, mode):
        open_calls.append(path)
        if len(open_calls) == 1:
            raise OSError("Permission denied")
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        return m

    with patch("builtins.open", fake_open), patch("os.makedirs"):
        results = await writer.write(output_id="out-1")

    assert len(results) == 2
    assert len(upsert_calls) == 2
    failed = [r for r in upsert_calls if not r["succeeded"]]
    succeeded = [r for r in upsert_calls if r["succeeded"]]
    assert len(failed) == 1
    assert len(succeeded) == 1
    assert "Permission denied" in failed[0]["error"]


@pytest.mark.asyncio
async def test_write_oserror_does_not_abort_all_combinations():
    """Even if the first combination fails with OSError, the rest complete."""
    output = _make_output(path_template="/cfg/{env}.json", fmt="json")
    dimensions = [
        _make_dim("env-a", "type-env", "a"),
        _make_dim("env-b", "type-env", "b"),
        _make_dim("env-c", "type-env", "c"),
    ]
    dimension_types = [{"id": "type-env", "name": "env"}]

    upsert_calls = []

    async def fake_upsert(**kwargs):
        upsert_calls.append(kwargs)
        return {**kwargs}

    writer = _make_writer(output=output, dimensions=dimensions, dimension_types=dimension_types)
    writer._outputs.upsert_result = fake_upsert

    open_calls = [0]

    def fake_open(path, mode):
        open_calls[0] += 1
        if open_calls[0] == 1:
            raise OSError("disk full")
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        return m

    with patch("builtins.open", fake_open), patch("os.makedirs"):
        results = await writer.write(output_id="out-1")

    assert len(results) == 3
    assert sum(1 for r in upsert_calls if not r["succeeded"]) == 1
    assert sum(1 for r in upsert_calls if r["succeeded"]) == 2


# ---------------------------------------------------------------------------
# ValueError (no configs) handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_value_error_records_failed_result_and_continues():
    """ValueError from resolve_scope is caught; remaining combinations continue."""
    output = _make_output(path_template="/cfg/{env}.json", fmt="json")
    dimensions = [
        _make_dim("env-prod", "type-env", "prod"),
        _make_dim("env-staging", "type-env", "staging"),
    ]
    dimension_types = [{"id": "type-env", "name": "env"}]

    upsert_calls = []

    async def fake_upsert(**kwargs):
        upsert_calls.append(kwargs)
        return {**kwargs}

    # resolve_scope raises ValueError for first call, succeeds for second.
    call_count = [0]

    async def fake_resolve_scope(*, configs, dimension_ids):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ValueError("No configurations found for scope")
        return {"key": "value"}

    writer = _make_writer(output=output, dimensions=dimensions, dimension_types=dimension_types)
    writer._orchestrator.resolve_scope = fake_resolve_scope
    writer._orchestrator.serialize = MagicMock(return_value=('{"key": "value"}', "application/json"))
    writer._outputs.upsert_result = fake_upsert

    with patch("builtins.open", MagicMock()), patch("os.makedirs"):
        results = await writer.write(output_id="out-1")

    assert len(results) == 2
    failed = [r for r in upsert_calls if not r["succeeded"]]
    succeeded = [r for r in upsert_calls if r["succeeded"]]
    assert len(failed) == 1
    assert len(succeeded) == 1
    assert "No configurations found" in failed[0]["error"]


@pytest.mark.asyncio
async def test_write_no_configs_does_not_abort_all_combinations():
    """All combinations get upsert_result called even when some have no configs."""
    output = _make_output(path_template="/cfg/{env}.json", fmt="json")
    dimensions = [
        _make_dim("env-a", "type-env", "a"),
        _make_dim("env-b", "type-env", "b"),
        _make_dim("env-c", "type-env", "c"),
    ]
    dimension_types = [{"id": "type-env", "name": "env"}]

    upsert_calls = []

    async def fake_upsert(**kwargs):
        upsert_calls.append(kwargs)
        return {**kwargs}

    # resolve_scope always raises ValueError
    writer = _make_writer(
        output=output,
        dimensions=dimensions,
        resolve_raises=ValueError("No configurations found for scope"),
        dimension_types=dimension_types,
    )
    writer._outputs.upsert_result = fake_upsert

    await writer.write(output_id="out-1")

    assert len(upsert_calls) == 3
    assert all(not r["succeeded"] for r in upsert_calls)
