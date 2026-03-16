import json
import logging

import tomli_w
import yaml
from fastapi import APIRouter, Request
from fastapi.responses import Response

from lanterna_magica.config import settings
from lanterna_magica.data.configurations import Configurations
from lanterna_magica.data.dimension_types import DimensionTypes
from lanterna_magica.data.dimensions import Dimensions
from lanterna_magica.data.shared_values import SharedValues
from lanterna_magica.errors import NotFoundError
from lanterna_magica.orchestrator.configuration import ConfigurationOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

_FORMATS = {"json", "yml", "toml"}


def _sanitize_for_toml(obj):
    """Recursively make obj safe for tomli_w.dumps.

    - dict: drop keys whose value is None; recurse into remaining values.
    - list: drop None elements; recurse into remaining elements.
    - all other values: return as-is.
    """
    if isinstance(obj, dict):
        return {
            k: _sanitize_for_toml(v) for k, v in obj.items() if v is not None
        }
    if isinstance(obj, list):
        # Drop None elements, then recurse into each remaining element
        return [_sanitize_for_toml(item) for item in obj if item is not None]
    return obj


@router.get("/{slug}")
async def get_config(slug: str, request: Request) -> Response:
    # Split on last '.' to extract name and format
    if "." not in slug:
        return Response(
            content=json.dumps({"detail": "Invalid slug: missing format extension"}),
            status_code=400,
            media_type="application/json",
        )

    dot_pos = slug.rfind(".")
    name = slug[:dot_pos]
    fmt = slug[dot_pos + 1 :]

    if fmt not in _FORMATS:
        detail = f"Unknown format '{fmt}'. Accepted: json, yml, toml"
        return Response(
            content=json.dumps({"detail": detail}),
            status_code=400,
            media_type="application/json",
        )

    pool = request.app.state.pool
    orchestrator = ConfigurationOrchestrator(
        configurations=Configurations(pool),
        shared_values=SharedValues(pool),
        dimension_types=DimensionTypes(pool),
        dimensions=Dimensions(pool),
        slug_dimension_type_name=settings.get("rest.slug_dimension_type_name", ""),
    )
    try:
        result = await orchestrator.resolve_from_names(
            slug_name=name, extra_dimensions=dict(request.query_params)
        )
    except (NotFoundError, ValueError) as exc:
        return Response(json.dumps({"detail": str(exc)}), 404, media_type="application/json")  # noqa: E501

    # Serialize based on format
    if fmt == "json":
        body = json.dumps(result)
        media_type = "application/json"
    elif fmt == "yml":
        body = yaml.dump(result)
        media_type = "text/yaml"
    else:  # toml
        body = tomli_w.dumps(_sanitize_for_toml(result))
        media_type = "application/toml"

    return Response(content=body, media_type=media_type)
