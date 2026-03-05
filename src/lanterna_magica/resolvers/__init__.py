import logging
from importlib.resources import files

from ariadne import load_schema_from_path, make_executable_schema
from ariadne.asgi import GraphQL
from graphql import GraphQLError

from lanterna_magica.data.configurations import Configurations
from lanterna_magica.data.environments import Environments
from lanterna_magica.data.loaders import create_loaders
from lanterna_magica.data.services import Services
from lanterna_magica.data.shared_values import SharedValues
from lanterna_magica.errors import AppError
from lanterna_magica.resolvers.configuration import get_configuration_resolvers
from lanterna_magica.resolvers.environment import get_environment_resolvers
from lanterna_magica.resolvers.scalars import datetime_scalar, json_scalar
from lanterna_magica.resolvers.service import get_service_resolvers
from lanterna_magica.resolvers.shared_value import get_shared_value_resolvers

logger = logging.getLogger(__name__)

SCHEMA_DIR = files("lanterna_magica").joinpath("schema")


def format_error(error: GraphQLError, debug: bool = False) -> dict:
    formatted = error.formatted
    original = error.original_error
    if isinstance(original, AppError):
        formatted.setdefault("extensions", {})["code"] = original.code
    elif original is not None:
        logger.exception("Unhandled error in GraphQL resolver", exc_info=original)
        formatted["message"] = "Internal server error"
        formatted.setdefault("extensions", {})["code"] = "INTERNAL_ERROR"
    return formatted


def create_gql(pool) -> GraphQL:
    configurations = Configurations(pool)
    environments = Environments(pool)
    services = Services(pool)
    shared_values = SharedValues(pool)

    type_defs = load_schema_from_path(str(SCHEMA_DIR))
    schema = make_executable_schema(
        type_defs,
        *get_configuration_resolvers(configurations),
        *get_environment_resolvers(environments),
        *get_service_resolvers(services),
        *get_shared_value_resolvers(shared_values),
        datetime_scalar,
        json_scalar,
        convert_names_case=True,
    )
    return GraphQL(
        schema,
        context_value=lambda request, _data=None: {
            "pool": pool,
            **create_loaders(pool),
        },
        error_formatter=format_error,
    )
