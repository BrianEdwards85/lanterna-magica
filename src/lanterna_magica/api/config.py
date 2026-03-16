import json
import logging

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

_FORMATS = {"json", "yml", "toml", "env"}


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
        detail = f"Unknown format '{fmt}'. Accepted: json, yml, toml, env"
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
        return Response(
            json.dumps({"detail": str(exc)}), 404, media_type="application/json"
        )

    body, media_type = orchestrator.serialize(result, fmt)
    return Response(content=body, media_type=media_type)
