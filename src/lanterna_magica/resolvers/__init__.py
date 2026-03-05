from pathlib import Path

from ariadne import load_schema_from_path, make_executable_schema
from ariadne.asgi import GraphQL

from lanterna_magica.data.environments import Environments
from lanterna_magica.data.services import Services
from lanterna_magica.data.shared_values import SharedValues
from lanterna_magica.resolvers.environment import get_environment_resolvers
from lanterna_magica.resolvers.scalars import datetime_scalar
from lanterna_magica.resolvers.service import get_service_resolvers
from lanterna_magica.resolvers.shared_value import get_shared_value_resolvers

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"


def create_gql(pool) -> GraphQL:
    environments = Environments(pool)
    services = Services(pool)
    shared_values = SharedValues(pool)

    type_defs = load_schema_from_path(str(SCHEMA_DIR))
    schema = make_executable_schema(
        type_defs,
        *get_environment_resolvers(environments),
        *get_service_resolvers(services),
        *get_shared_value_resolvers(shared_values),
        datetime_scalar,
        convert_names_case=True,
    )
    return GraphQL(
        schema,
        context_value=lambda request, _data=None: {"pool": pool},
    )
