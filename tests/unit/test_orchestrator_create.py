import pytest
from helpers import _make_orchestrator

from lanterna_magica.errors import ValidationError
from lanterna_magica.orchestrator.configuration import ConfigurationOrchestrator

# -- create_configuration validation --


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
    assert result == {
        "db": {"password": "db-pass"},
        "cache": {"secret": "cache-secret"},
    }


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
