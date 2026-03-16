from unittest.mock import AsyncMock

import pytest

from lanterna_magica.errors import ValidationError
from lanterna_magica.orchestrator.configuration import ConfigurationOrchestrator

# -- flat dict --


def test_flat_dict_sentinel_found():
    result = ConfigurationOrchestrator.find_sentinel_paths({"password": "_"})
    assert result == ["$.password"]


def test_flat_dict_no_sentinel():
    result = ConfigurationOrchestrator.find_sentinel_paths(
        {"host": "localhost", "port": 5432}
    )
    assert result == []


def test_flat_dict_mixed():
    result = ConfigurationOrchestrator.find_sentinel_paths(
        {"host": "localhost", "password": "_"}
    )
    assert result == ["$.password"]


# -- nested dict --


def test_nested_dict_sentinel_found():
    result = ConfigurationOrchestrator.find_sentinel_paths(
        {"db": {"host": "localhost", "password": "_"}}
    )
    assert result == ["$.db.password"]


def test_nested_dict_multiple_sentinels():
    result = ConfigurationOrchestrator.find_sentinel_paths(
        {"db": {"password": "_"}, "cache": {"secret": "_"}}
    )
    assert set(result) == {"$.db.password", "$.cache.secret"}


def test_nested_dict_no_sentinel():
    result = ConfigurationOrchestrator.find_sentinel_paths(
        {"db": {"host": "localhost", "port": 5432}}
    )
    assert result == []


# -- array of scalars --


def test_array_of_scalars_sentinel_found():
    result = ConfigurationOrchestrator.find_sentinel_paths({"keys": ["_", "real"]})
    assert result == ["$.keys[0]"]


def test_array_of_scalars_no_sentinel():
    result = ConfigurationOrchestrator.find_sentinel_paths({"keys": ["a", "b", "c"]})
    assert result == []


def test_array_of_scalars_multiple_sentinels():
    result = ConfigurationOrchestrator.find_sentinel_paths({"keys": ["_", "_", "real"]})
    assert result == ["$.keys[0]", "$.keys[1]"]


# -- array of objects --


def test_array_of_objects_sentinel_found():
    result = ConfigurationOrchestrator.find_sentinel_paths(
        {"servers": [{"host": "localhost", "password": "_"}]}
    )
    assert result == ["$.servers[0].password"]


def test_array_of_objects_multiple_elements():
    result = ConfigurationOrchestrator.find_sentinel_paths(
        {"servers": [{"password": "_"}, {"password": "real"}, {"password": "_"}]}
    )
    assert result == ["$.servers[0].password", "$.servers[2].password"]


# -- deeply nested mixed structures --


def test_deeply_nested_mixed():
    body = {
        "db": {"host": "localhost", "password": "_"},
        "keys": ["_", "real"],
    }
    result = ConfigurationOrchestrator.find_sentinel_paths(body)
    assert set(result) == {"$.db.password", "$.keys[0]"}


def test_servers_password_mixed():
    body = {"servers": [{"host": "web1", "password": "_"}]}
    result = ConfigurationOrchestrator.find_sentinel_paths(body)
    assert result == ["$.servers[0].password"]


def test_deeply_nested_array_in_dict_in_array():
    body = {"outer": [{"inner": {"secret": "_"}}]}
    result = ConfigurationOrchestrator.find_sentinel_paths(body)
    assert result == ["$.outer[0].inner.secret"]


# -- empty body --


def test_empty_body():
    result = ConfigurationOrchestrator.find_sentinel_paths({})
    assert result == []


# -- body with no sentinels --


def test_body_with_no_sentinels():
    body = {
        "service": "my-service",
        "replicas": 3,
        "enabled": True,
        "tags": ["web", "api"],
        "db": {"host": "localhost", "port": 5432},
    }
    result = ConfigurationOrchestrator.find_sentinel_paths(body)
    assert result == []


# -- sentinel value exclusivity --


def test_underscore_string_only_not_null():
    result = ConfigurationOrchestrator.find_sentinel_paths({"a": None})
    assert result == []


def test_underscore_string_only_not_number():
    result = ConfigurationOrchestrator.find_sentinel_paths({"a": 0})
    assert result == []


def test_underscore_string_only_not_false():
    result = ConfigurationOrchestrator.find_sentinel_paths({"a": False})
    assert result == []


def test_underscore_string_only_not_double_underscore():
    result = ConfigurationOrchestrator.find_sentinel_paths({"a": "__"})
    assert result == []


def test_underscore_string_only_not_empty_string():
    result = ConfigurationOrchestrator.find_sentinel_paths({"a": ""})
    assert result == []


def test_sentinel_is_exact_string_underscore():
    result = ConfigurationOrchestrator.find_sentinel_paths(
        {"a": "_", "b": "__", "c": None}
    )
    assert result == ["$.a"]


# -- non-leaf objects and arrays are not returned --


def test_dict_value_not_returned_as_sentinel():
    result = ConfigurationOrchestrator.find_sentinel_paths({"nested": {"key": "value"}})
    assert result == []


def test_array_value_not_returned_as_sentinel():
    result = ConfigurationOrchestrator.find_sentinel_paths({"list": [1, 2, 3]})
    assert result == []


# -- create_configuration validation --


def _make_orchestrator():
    mock_configs = AsyncMock()
    mock_configs.create_configuration = AsyncMock(
        return_value={"id": "fake-id", "substitutions": []}
    )
    mock_shared_values = AsyncMock()
    return ConfigurationOrchestrator(mock_configs, mock_shared_values)


@pytest.mark.asyncio
async def test_create_configuration_happy_path_calls_data_layer():
    """Matching sentinel and substitution passes validation and delegates."""
    orch = _make_orchestrator()
    sv_id = "sv-abc"
    result = await orch.create_configuration(
        body={"x": "_"},
        dimension_ids=["dim-1"],
        substitutions=[{"jsonpath": "$.x", "shared_value_id": sv_id}],
    )
    assert result["id"] == "fake-id"
    orch._configurations.create_configuration.assert_called_once()


@pytest.mark.asyncio
async def test_create_configuration_missing_substitution_raises():
    """Sentinel in body with no matching substitution raises ValidationError."""
    orch = _make_orchestrator()
    with pytest.raises(ValidationError) as exc_info:
        await orch.create_configuration(
            body={"x": "_"},
            dimension_ids=["dim-1"],
            substitutions=None,
        )
    assert "$.x" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_configuration_extra_substitution_raises():
    """Substitution for a path not in body raises ValidationError."""
    orch = _make_orchestrator()
    with pytest.raises(ValidationError) as exc_info:
        await orch.create_configuration(
            body={"x": 1},
            dimension_ids=["dim-1"],
            substitutions=[{"jsonpath": "$.y", "shared_value_id": "sv-abc"}],
        )
    assert "$.y" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_configuration_no_sentinels_no_substitutions_passes():
    """Body with no sentinels and no substitutions passes validation."""
    orch = _make_orchestrator()
    result = await orch.create_configuration(
        body={"key": "value"},
        dimension_ids=["dim-1"],
        substitutions=None,
    )
    assert result["id"] == "fake-id"
    orch._configurations.create_configuration.assert_called_once()


@pytest.mark.asyncio
async def test_create_configuration_missing_and_extra_substitutions_raises():
    """Mismatched substitutions (both missing and extra) raises ValidationError."""
    orch = _make_orchestrator()
    with pytest.raises(ValidationError):
        await orch.create_configuration(
            body={"a": "_"},
            dimension_ids=["dim-1"],
            substitutions=[{"jsonpath": "$.b", "shared_value_id": "sv-abc"}],
        )


# -- apply_substitutions --


def test_apply_substitutions_flat():
    body = {"password": "_", "host": "localhost"}
    resolved = {"$.password": "secret123"}
    result = ConfigurationOrchestrator.apply_substitutions(body, resolved)
    assert result == {"password": "secret123", "host": "localhost"}


def test_apply_substitutions_nested():
    body = {"db": {"host": "localhost", "password": "_"}}
    resolved = {"$.db.password": "secret"}
    result = ConfigurationOrchestrator.apply_substitutions(body, resolved)
    assert result == {"db": {"host": "localhost", "password": "secret"}}


def test_apply_substitutions_array_index():
    body = {"keys": ["_", "real"]}
    resolved = {"$.keys[0]": "resolved_key"}
    result = ConfigurationOrchestrator.apply_substitutions(body, resolved)
    assert result == {"keys": ["resolved_key", "real"]}


def test_apply_substitutions_array_of_objects():
    body = {"servers": [{"host": "web1", "password": "_"}]}
    resolved = {"$.servers[0].password": "s3cr3t"}
    result = ConfigurationOrchestrator.apply_substitutions(body, resolved)
    assert result == {"servers": [{"host": "web1", "password": "s3cr3t"}]}


def test_apply_substitutions_multiple_paths():
    body = {"db": {"password": "_"}, "cache": {"secret": "_"}}
    resolved = {"$.db.password": "db-pass", "$.cache.secret": "cache-secret"}
    result = ConfigurationOrchestrator.apply_substitutions(body, resolved)
    assert result == {"db": {"password": "db-pass"}, "cache": {"secret": "cache-secret"}}


def test_apply_substitutions_does_not_mutate_original():
    body = {"password": "_"}
    resolved = {"$.password": "new-value"}
    ConfigurationOrchestrator.apply_substitutions(body, resolved)
    assert body == {"password": "_"}


def test_apply_substitutions_no_resolved_returns_body_unchanged():
    body = {"host": "localhost", "port": 5432}
    result = ConfigurationOrchestrator.apply_substitutions(body, {})
    assert result == body


def test_apply_substitutions_unresolved_sentinel_stays_as_sentinel():
    """A path mapped to '_' (unresolvable) remains '_' in the output."""
    body = {"password": "_"}
    resolved = {"$.password": "_"}
    result = ConfigurationOrchestrator.apply_substitutions(body, resolved)
    assert result == {"password": "_"}


def test_apply_substitutions_deeply_nested_array_in_dict_in_array():
    body = {"outer": [{"inner": {"secret": "_"}}]}
    resolved = {"$.outer[0].inner.secret": "found"}
    result = ConfigurationOrchestrator.apply_substitutions(body, resolved)
    assert result == {"outer": [{"inner": {"secret": "found"}}]}


# -- apply_projection --


def _make_orchestrator_with_sv(resolve_return_value):
    mock_configs = AsyncMock()
    mock_shared_values = AsyncMock()
    mock_shared_values.resolve_for_scope = AsyncMock(
        return_value=resolve_return_value
    )
    return ConfigurationOrchestrator(mock_configs, mock_shared_values)


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


# -- resolve_scope --


def _make_config(body: dict, substitutions: list[dict] | None = None) -> dict:
    """Helper: build a config dict as the data layer returns it (body as dict)."""
    return {"body": body, "substitutions": substitutions or []}


@pytest.mark.asyncio
async def test_resolve_scope_empty_configs_raises():
    """Empty configs list raises ValueError."""
    orch = _make_orchestrator()
    with pytest.raises(ValueError, match="No configurations found for scope"):
        await orch.resolve_scope(configs=[], dimension_ids=["dim-1"])


@pytest.mark.asyncio
async def test_resolve_scope_single_config_no_substitutions():
    """Single config with no substitutions is returned as-is."""
    orch = _make_orchestrator()
    configs = [_make_config({"host": "localhost", "port": 5432})]
    result = await orch.resolve_scope(configs=configs, dimension_ids=["dim-1"])
    assert result == {"host": "localhost", "port": 5432}


@pytest.mark.asyncio
async def test_resolve_scope_two_configs_later_overwrites_earlier():
    """Later (more specific) config keys overwrite earlier (less specific) ones."""
    orch = _make_orchestrator()
    configs = [
        _make_config({"host": "default-host", "port": 5432, "debug": False}),
        _make_config({"host": "prod-host", "debug": True}),
    ]
    result = await orch.resolve_scope(configs=configs, dimension_ids=["dim-1"])
    assert result == {"host": "prod-host", "port": 5432, "debug": True}


@pytest.mark.asyncio
async def test_resolve_scope_merge_order_earlier_keys_not_overwritten():
    """Keys present only in the first config survive the merge."""
    orch = _make_orchestrator()
    configs = [
        _make_config({"a": 1, "b": 2}),
        _make_config({"b": 99, "c": 3}),
    ]
    result = await orch.resolve_scope(configs=configs, dimension_ids=["dim-1"])
    assert result == {"a": 1, "b": 99, "c": 3}


@pytest.mark.asyncio
async def test_resolve_scope_config_with_substitutions():
    """Substitutions are resolved and applied during merge."""
    mock_configs = AsyncMock()
    mock_shared_values = AsyncMock()
    mock_shared_values.resolve_for_scope = AsyncMock(return_value={"value": "s3cr3t"})
    orch = ConfigurationOrchestrator(mock_configs, mock_shared_values)

    configs = [
        _make_config(
            {"host": "localhost", "password": "_"},
            substitutions=[{"jsonpath": "$.password", "shared_value_id": "sv-1"}],
        )
    ]
    result = await orch.resolve_scope(configs=configs, dimension_ids=["dim-1"])
    assert result == {"host": "localhost", "password": "s3cr3t"}
    mock_shared_values.resolve_for_scope.assert_awaited_once_with(
        shared_value_id="sv-1",
        dimension_ids=["dim-1"],
    )


@pytest.mark.asyncio
async def test_resolve_scope_config_with_no_substitutions_field():
    """Config with an empty substitutions list is projected without shared-value calls."""
    orch = _make_orchestrator_with_sv(None)
    configs = [_make_config({"key": "value"}, substitutions=[])]
    result = await orch.resolve_scope(configs=configs, dimension_ids=["dim-1"])
    assert result == {"key": "value"}
    orch._shared_values.resolve_for_scope.assert_not_awaited()


