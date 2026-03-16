from unittest.mock import AsyncMock

import pytest
from helpers import _make_orchestrator_with_sv

from lanterna_magica.orchestrator.configuration import ConfigurationOrchestrator

# -- apply_projection --


@pytest.mark.asyncio
async def test_apply_projection_replaces_sentinel_with_revision_value():
    orch = _make_orchestrator_with_sv({"value": "s3cr3t"})
    result = await orch.apply_projection(
        body={"password": "_"},
        substitutions=[{"jsonpath": "$.password", "shared_value_id": "sv-1"}],
        dimension_ids=["dim-1", "dim-2"],
    )
    assert result == {"password": "s3cr3t"}
    orch._shared_values.resolve_for_scope.assert_awaited_once_with(
        shared_value_id="sv-1",
        dimension_ids=["dim-1", "dim-2"],
    )


@pytest.mark.asyncio
async def test_apply_projection_unresolvable_leaves_sentinel():
    orch = _make_orchestrator_with_sv(None)
    result = await orch.apply_projection(
        body={"api_key": "_"},
        substitutions=[{"jsonpath": "$.api_key", "shared_value_id": "sv-2"}],
        dimension_ids=["dim-1"],
    )
    assert result == {"api_key": "_"}


@pytest.mark.asyncio
async def test_apply_projection_no_substitutions_returns_body_unchanged():
    orch = _make_orchestrator_with_sv(None)
    result = await orch.apply_projection(
        body={"host": "localhost"},
        substitutions=[],
        dimension_ids=["dim-1"],
    )
    assert result == {"host": "localhost"}
    orch._shared_values.resolve_for_scope.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_projection_multiple_substitutions_all_resolved():
    """Multiple substitutions are resolved concurrently and all applied."""
    mock_configs = AsyncMock()
    mock_shared_values = AsyncMock()
    mock_shared_values.resolve_for_scope = AsyncMock(
        side_effect=[
            {"value": "db-pass"},
            {"value": "cache-secret"},
        ]
    )
    orch = ConfigurationOrchestrator(mock_configs, mock_shared_values)
    result = await orch.apply_projection(
        body={"db": {"password": "_"}, "cache": {"secret": "_"}},
        substitutions=[
            {"jsonpath": "$.db.password", "shared_value_id": "sv-1"},
            {"jsonpath": "$.cache.secret", "shared_value_id": "sv-2"},
        ],
        dimension_ids=["dim-1"],
    )
    expected = {"db": {"password": "db-pass"}, "cache": {"secret": "cache-secret"}}
    assert result == expected
    assert mock_shared_values.resolve_for_scope.await_count == 2


@pytest.mark.asyncio
async def test_apply_projection_multiple_substitutions_partial_resolved():
    """Unresolvable substitutions leave sentinel in place while others are resolved."""
    mock_configs = AsyncMock()
    mock_shared_values = AsyncMock()
    mock_shared_values.resolve_for_scope = AsyncMock(
        side_effect=[
            {"value": "db-pass"},
            None,
        ]
    )
    orch = ConfigurationOrchestrator(mock_configs, mock_shared_values)
    result = await orch.apply_projection(
        body={"db": {"password": "_"}, "cache": {"secret": "_"}},
        substitutions=[
            {"jsonpath": "$.db.password", "shared_value_id": "sv-1"},
            {"jsonpath": "$.cache.secret", "shared_value_id": "sv-2"},
        ],
        dimension_ids=["dim-1"],
    )
    assert result == {"db": {"password": "db-pass"}, "cache": {"secret": "_"}}


@pytest.mark.asyncio
async def test_apply_projection_error_propagation():
    """asyncio.gather uses return_exceptions=False (fail-fast): an exception from
    any resolve_for_scope call propagates immediately out of apply_projection."""
    mock_configs = AsyncMock()
    mock_shared_values = AsyncMock()
    mock_shared_values.resolve_for_scope = AsyncMock(
        side_effect=[
            {"value": "db-pass"},
            RuntimeError("shared value backend unavailable"),
        ]
    )
    orch = ConfigurationOrchestrator(mock_configs, mock_shared_values)
    with pytest.raises(RuntimeError, match="shared value backend unavailable"):
        await orch.apply_projection(
            body={"db": {"password": "_"}, "cache": {"secret": "_"}},
            substitutions=[
                {"jsonpath": "$.db.password", "shared_value_id": "sv-1"},
                {"jsonpath": "$.cache.secret", "shared_value_id": "sv-2"},
            ],
            dimension_ids=["dim-1"],
        )
