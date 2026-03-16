import json
from unittest.mock import AsyncMock

import pytest
import yaml
from helpers import _make_config, _make_orchestrator, _make_orchestrator_with_sv

from lanterna_magica.orchestrator.configuration import ConfigurationOrchestrator

# -- resolve_scope --


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


# -- serialize --


@pytest.mark.unit
def test_serialize_json_format():
    orch = _make_orchestrator()
    result = {"host": "localhost", "port": 5432}
    body, media_type = orch.serialize(result, "json")
    assert media_type == "application/json"
    parsed = json.loads(body)
    assert parsed == result


@pytest.mark.unit
def test_serialize_yml_format():
    orch = _make_orchestrator()
    result = {"host": "localhost", "port": 5432}
    body, media_type = orch.serialize(result, "yml")
    assert media_type == "text/yaml"
    parsed = yaml.safe_load(body)
    assert parsed == result


@pytest.mark.unit
def test_serialize_toml_format_basic():
    orch = _make_orchestrator()
    result = {"host": "localhost", "port": 5432}
    body, media_type = orch.serialize(result, "toml")
    assert media_type == "application/toml"
    assert "host" in body
    assert "port" in body


@pytest.mark.unit
def test_serialize_toml_null_value_dropped():
    orch = _make_orchestrator()
    result = {"host": "localhost", "password": None, "port": 5432}
    body, media_type = orch.serialize(result, "toml")
    assert media_type == "application/toml"
    assert "host" in body
    assert "port" in body
    assert "password" not in body


@pytest.mark.unit
def test_serialize_toml_mixed_type_array_stringified():
    """After _sanitize_for_toml, None elements are dropped from arrays."""
    orch = _make_orchestrator()
    result = {"tags": ["alpha", None, "beta"]}
    body, media_type = orch.serialize(result, "toml")
    assert media_type == "application/toml"
    assert "alpha" in body
    assert "beta" in body


@pytest.mark.unit
def test_serialize_env_format_scalar_values():
    orch = _make_orchestrator()
    result = {"HOST": "localhost", "PORT": 5432, "DEBUG": True, "RATIO": 1.5}
    body, media_type = orch.serialize(result, "env")
    assert media_type == "text/plain"
    lines = body.splitlines()
    assert "HOST=localhost" in lines
    assert "PORT=5432" in lines
    assert "DEBUG=True" in lines
    assert "RATIO=1.5" in lines


@pytest.mark.unit
def test_serialize_env_format_non_scalar_json_encoded():
    orch = _make_orchestrator()
    result = {"TAGS": ["a", "b"], "DB": {"host": "localhost"}}
    body, media_type = orch.serialize(result, "env")
    assert media_type == "text/plain"
    lines = body.splitlines()
    tags_line = next(line for line in lines if line.startswith("TAGS="))
    db_line = next(line for line in lines if line.startswith("DB="))
    assert json.loads(tags_line[len("TAGS=") :]) == ["a", "b"]
    assert json.loads(db_line[len("DB=") :]) == {"host": "localhost"}


@pytest.mark.unit
def test_serialize_unknown_format_raises_value_error():
    orch = _make_orchestrator()
    with pytest.raises(ValueError, match="Unknown format"):
        orch.serialize({"key": "value"}, "xml")
