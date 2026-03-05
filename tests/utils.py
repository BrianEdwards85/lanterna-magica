from datetime import datetime

from conftest import gql

# -- Shared GQL Mutations (minimal field sets for test setup) --

_CREATE_SERVICE = """
mutation CreateService($input: CreateServiceInput!) {
    createService(input: $input) { id name }
}
"""

_CREATE_ENVIRONMENT = """
mutation CreateEnvironment($input: CreateEnvironmentInput!) {
    createEnvironment(input: $input) { id name }
}
"""

_CREATE_SHARED_VALUE = """
mutation CreateSharedValue($input: CreateSharedValueInput!) {
    createSharedValue(input: $input) { id name }
}
"""

_CREATE_REVISION = """
mutation CreateSharedValueRevision($input: CreateSharedValueRevisionInput!) {
    createSharedValueRevision(input: $input) {
        id sharedValue { id } serviceId { id } environmentId { id } value isCurrent createdAt
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


async def create_shared_value(client, name="db_password"):
    body = await gql(client, _CREATE_SHARED_VALUE, {"input": {"name": name}})
    return body["data"]["createSharedValue"]


async def create_revision(client, shared_value_id, service_id, environment_id, value):
    body = await gql(
        client,
        _CREATE_REVISION,
        {
            "input": {
                "sharedValueId": shared_value_id,
                "serviceId": service_id,
                "environmentId": environment_id,
                "value": value,
            }
        },
    )
    return body["data"]["createSharedValueRevision"]
