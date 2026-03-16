import logging
from importlib.resources import files

from ariadne import load_schema_from_path, make_executable_schema
from ariadne.asgi import GraphQL
from ariadne.asgi.handlers import GraphQLHTTPHandler
from ariadne.contrib.tracing.opentelemetry import opentelemetry_extension
from graphql import GraphQLError

from lanterna_magica.data.configurations import Configurations
from lanterna_magica.data.dimension_types import DimensionTypes
from lanterna_magica.data.dimensions import Dimensions
from lanterna_magica.data.loaders import create_loaders
from lanterna_magica.data.outputs import Outputs
from lanterna_magica.data.shared_values import SharedValues
from lanterna_magica.errors import AppError
from lanterna_magica.orchestrator import ConfigurationOrchestrator
from lanterna_magica.resolvers.configuration import get_configuration_resolvers
from lanterna_magica.resolvers.dimension import get_dimension_resolvers
from lanterna_magica.resolvers.dimension_facade import get_facade_resolvers
from lanterna_magica.resolvers.dimension_type import get_dimension_type_resolvers
from lanterna_magica.resolvers.output import get_output_resolvers
from lanterna_magica.resolvers.scalars import datetime_scalar, json_scalar
from lanterna_magica.resolvers.shared_value import get_shared_value_resolvers
from lanterna_magica.writer.outputs import OutputWriter

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
    dimension_types = DimensionTypes(pool)
    dimensions = Dimensions(pool)
    shared_values = SharedValues(pool)
    outputs = Outputs(pool)
    configuration_orchestrator = ConfigurationOrchestrator(
        configurations, shared_values
    )
    writer = OutputWriter(
        outputs, configurations, configuration_orchestrator, dimension_types
    )

    type_defs = load_schema_from_path(str(SCHEMA_DIR))
    schema = make_executable_schema(
        type_defs,
        *get_configuration_resolvers(configurations, configuration_orchestrator),
        *get_dimension_type_resolvers(dimension_types, dimensions),
        *get_dimension_resolvers(dimensions),
        *get_facade_resolvers(dimensions, dimension_types, "service"),
        *get_facade_resolvers(dimensions, dimension_types, "environment"),
        *get_shared_value_resolvers(shared_values, configurations),
        *get_output_resolvers(outputs, writer),
        datetime_scalar,
        json_scalar,
        convert_names_case=True,
    )
    return GraphQL(
        schema,
        context_value=lambda request, _data=None: {
            **create_loaders(pool),
        },
        error_formatter=format_error,
        http_handler=GraphQLHTTPHandler(
            extensions=[opentelemetry_extension()],
        ),
    )
