"""Unit tests for OutputWriter."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lanterna_magica.errors import NotFoundError
from lanterna_magica.writer.outputs import OutputWriter, _render_path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dim(id: str, type_id: str, name: str, base: bool = False) -> dict:
    return {
        "id": id, "type_id": type_id, "name": name,
        "base": base, "archived_at": None,
    }


def _make_output(
    id: str = "out-1",
    path_template: str = "/etc/configs/{environment}/{service}.json",
    fmt: str = "json",
    archived_at=None,
) -> dict:
    return {
        "id": id,
        "path_template": path_template,
        "format": fmt,
        "archived_at": archived_at,
    }


def _make_upsert_result(
    output_id: str,
    scope_hash: str,
    path: str,
    content: str,
    succeeded: bool,
    error: str | None = None,
) -> dict:
    return {
        "output_id": output_id,
        "scope_hash": scope_hash,
        "path": path,
        "content": content,
        "succeeded": succeeded,
        "error": error,
    }


def _make_writer(
    output: dict | None = None,
    dimensions: list[dict] | None = None,
    configs: list[dict] | None = None,
    resolve_return: dict | None = None,
    resolve_raises: Exception | None = None,
    upsert_result: dict | None = None,
    dimension_types: list[dict] | None = None,
):
    """Return an OutputWriter with all dependencies mocked."""
    mock_outputs = AsyncMock()
    mock_outputs.get = AsyncMock(return_value=output)
    mock_outputs.get_dimensions = AsyncMock(return_value=dimensions or [])
    mock_outputs.upsert_result = AsyncMock(
        return_value=upsert_result or {"succeeded": True}
    )

    mock_configurations = AsyncMock()
    mock_configurations.get_for_rest_scope = AsyncMock(return_value=configs or [])

    mock_orchestrator = MagicMock()
    if resolve_raises is not None:
        mock_orchestrator.resolve_scope = AsyncMock(side_effect=resolve_raises)
    else:
        mock_orchestrator.resolve_scope = AsyncMock(
            return_value=resolve_return or {"key": "value"}
        )
    mock_orchestrator.serialize = MagicMock(
        return_value=('{"key": "value"}', "application/json")
    )

    mock_dimension_types = AsyncMock()
    mock_dimension_types.get_dimension_types_by_ids = AsyncMock(
        return_value=dimension_types or []
    )

    return OutputWriter(
        mock_outputs, mock_configurations, mock_orchestrator, mock_dimension_types
    )


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

    with patch("builtins.open", MagicMock()), \
         patch("os.makedirs"):
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

    with patch("builtins.open", MagicMock()), \
         patch("os.makedirs"):
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

    with patch("builtins.open", MagicMock()), \
         patch("os.makedirs"):
        results = await writer.write(output_id="out-1")

    assert len(results) == 1
    assert len(upsert_calls) == 1


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

    with patch("builtins.open", MagicMock()), \
         patch("os.makedirs"):
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

        with patch("builtins.open", MagicMock()), \
             patch("os.makedirs"):
            await writer.write(output_id="out-1")

        writer._orchestrator.serialize.assert_called_with(
            writer._orchestrator.resolve_scope.return_value, fmt
        )


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

    writer = _make_writer(
        output=output, dimensions=dimensions, dimension_types=dimension_types
    )
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

    with patch("builtins.open", fake_open), \
         patch("os.makedirs"):
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

    writer = _make_writer(
        output=output, dimensions=dimensions, dimension_types=dimension_types
    )
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

    with patch("builtins.open", fake_open), \
         patch("os.makedirs"):
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

    writer = _make_writer(
        output=output, dimensions=dimensions, dimension_types=dimension_types
    )
    writer._orchestrator.resolve_scope = fake_resolve_scope
    writer._orchestrator.serialize = MagicMock(
        return_value=('{"key": "value"}', "application/json")
    )
    writer._outputs.upsert_result = fake_upsert

    with patch("builtins.open", MagicMock()), \
         patch("os.makedirs"):
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

    with patch("builtins.open", MagicMock()), \
         patch("os.makedirs"):
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

    with patch("builtins.open", MagicMock()), \
         patch("os.makedirs", fake_makedirs):
        await writer.write(output_id="out-1")

    assert len(makedirs_calls) == 1
    assert makedirs_calls[0] == ("/cfg/prod", True)
