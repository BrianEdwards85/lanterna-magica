from unittest.mock import AsyncMock, MagicMock

from lanterna_magica.orchestrator.configuration import ConfigurationOrchestrator
from lanterna_magica.writer.outputs import OutputWriter


def _make_orchestrator():
    mock_configs = AsyncMock()
    mock_configs.create_configuration = AsyncMock(return_value={"id": "fake-id", "substitutions": []})
    mock_shared_values = AsyncMock()
    return ConfigurationOrchestrator(mock_configs, mock_shared_values)


def _make_config(body: dict, substitutions: list[dict] | None = None) -> dict:
    """Helper: build a config dict as the data layer returns it (body as dict)."""
    return {"body": body, "substitutions": substitutions or []}


def _make_orchestrator_with_sv(resolve_return_value):
    mock_configs = AsyncMock()
    mock_shared_values = AsyncMock()
    mock_shared_values.resolve_for_scope = AsyncMock(return_value=resolve_return_value)
    return ConfigurationOrchestrator(mock_configs, mock_shared_values)


# ---------------------------------------------------------------------------
# OutputWriter factory helpers
# ---------------------------------------------------------------------------


def _make_dim(id: str, type_id: str, name: str, base: bool = False) -> dict:
    return {
        "id": id,
        "type_id": type_id,
        "name": name,
        "base": base,
        "archived_at": None,
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
    mock_outputs.upsert_result = AsyncMock(return_value=upsert_result or {"succeeded": True})

    mock_configurations = AsyncMock()
    mock_configurations.get_for_rest_scope = AsyncMock(return_value=configs or [])

    mock_orchestrator = MagicMock()
    if resolve_raises is not None:
        mock_orchestrator.resolve_scope = AsyncMock(side_effect=resolve_raises)
    else:
        mock_orchestrator.resolve_scope = AsyncMock(return_value=resolve_return or {"key": "value"})
    mock_orchestrator.serialize = MagicMock(return_value=('{"key": "value"}', "application/json"))

    mock_dimension_types = AsyncMock()
    mock_dimension_types.get_dimension_types_by_ids = AsyncMock(return_value=dimension_types or [])

    return OutputWriter(mock_outputs, mock_configurations, mock_orchestrator, mock_dimension_types)
