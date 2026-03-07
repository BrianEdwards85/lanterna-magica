from datetime import datetime

from conftest import gql

# -- Shared GQL Mutations --

_CREATE_SERVICE = """
mutation CreateService($input: CreateServiceInput!) {
    createService(input: $input) {
        id name description createdAt updatedAt archivedAt
    }
}
"""

_CREATE_ENVIRONMENT = """
mutation CreateEnvironment($input: CreateEnvironmentInput!) {
    createEnvironment(input: $input) {
        id name description createdAt updatedAt archivedAt
    }
}
"""

_CREATE_DIMENSION_TYPE = """
mutation CreateDimensionType($input: CreateDimensionTypeInput!) {
    createDimensionType(input: $input) {
        id name priority createdAt archivedAt
    }
}
"""

_CREATE_DIMENSION = """
mutation CreateDimension($input: CreateDimensionInput!) {
    createDimension(input: $input) {
        id type { id name } name description base createdAt updatedAt archivedAt
    }
}
"""

_CREATE_SHARED_VALUE = """
mutation CreateSharedValue($input: CreateSharedValueInput!) {
    createSharedValue(input: $input) {
        id name createdAt updatedAt archivedAt
    }
}
"""

_CREATE_REVISION = """
mutation CreateSharedValueRevision($input: CreateSharedValueRevisionInput!) {
    createSharedValueRevision(input: $input) {
        id sharedValue { id } dimensions { id name } value isCurrent createdAt
    }
}
"""


# -- Helpers --


def parse_dt(iso_string):
    return datetime.fromisoformat(iso_string)


def nodes(edges):
    return [e["node"] for e in edges]


async def create_service(client, name="traefik", description=None):
    body = await gql(
        client, _CREATE_SERVICE, {"input": {"name": name, "description": description}}
    )
    return body["data"]["createService"]


async def create_environment(client, name="production", description=None):
    body = await gql(
        client, _CREATE_ENVIRONMENT, {"input": {"name": name, "description": description}}
    )
    return body["data"]["createEnvironment"]


async def create_dimension_type(client, name):
    body = await gql(
        client, _CREATE_DIMENSION_TYPE, {"input": {"name": name}}
    )
    return body["data"]["createDimensionType"]


async def create_dimension(client, type_id, name, description=None):
    body = await gql(
        client, _CREATE_DIMENSION, {"input": {"typeId": type_id, "name": name, "description": description}}
    )
    return body["data"]["createDimension"]


async def create_shared_value(client, name="db_password"):
    body = await gql(client, _CREATE_SHARED_VALUE, {"input": {"name": name}})
    return body["data"]["createSharedValue"]


async def create_revision(client, shared_value_id, dimension_ids, value):
    body = await gql(
        client,
        _CREATE_REVISION,
        {
            "input": {
                "sharedValueId": shared_value_id,
                "dimensionIds": dimension_ids,
                "value": value,
            }
        },
    )
    return body["data"]["createSharedValueRevision"]
