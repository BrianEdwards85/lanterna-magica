from pathlib import Path

from ariadne import load_schema_from_path, make_executable_schema
from ariadne.asgi import GraphQL

from lanterna_magica.data.services import Services
from lanterna_magica.resolvers.scalars import datetime_scalar
from lanterna_magica.resolvers.service import get_service_resolvers

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"


def create_gql(pool) -> GraphQL:
    services = Services(pool)

    type_defs = load_schema_from_path(str(SCHEMA_DIR))
    schema = make_executable_schema(
        type_defs,
        *get_service_resolvers(services),
        datetime_scalar,
        convert_names_case=True,
    )
    return GraphQL(
        schema,
        context_value=lambda request, _data=None: {"pool": pool},
    )
