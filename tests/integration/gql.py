"""Centralised GraphQL strings and GQL-calling helpers for integration tests."""

from conftest import gql

# ---------------------------------------------------------------------------
# Dimension Type GQL
# ---------------------------------------------------------------------------

GET_DIMENSION_TYPES = """
query DimensionTypes {
    dimensionTypes { id name }
}
"""

CREATE_DIMENSION_TYPE = """
mutation CreateDimensionType($input: CreateDimensionTypeInput!) {
    createDimensionType(input: $input) {
        id name priority createdAt archivedAt
    }
}
"""

ARCHIVE_DIMENSION_TYPE = """
mutation ArchiveDimensionType($id: ID!) {
    archiveDimensionType(id: $id) {
        id name archivedAt
    }
}
"""

UPDATE_DIMENSION_TYPE = """
mutation UpdateDimensionType($input: UpdateDimensionTypeInput!) {
    updateDimensionType(input: $input) {
        id name priority createdAt archivedAt
    }
}
"""

SWAP_DIMENSION_TYPE_PRIORITIES = """
mutation SwapDimensionTypePriorities($idA: ID!, $idB: ID!) {
    swapDimensionTypePriorities(idA: $idA, idB: $idB) {
        id name priority
    }
}
"""

UNARCHIVE_DIMENSION_TYPE = """
mutation UnarchiveDimensionType($id: ID!) {
    unarchiveDimensionType(id: $id) {
        id name archivedAt
    }
}
"""

DIMENSION_TYPES = """
query DimensionTypes($includeArchived: Boolean) {
    dimensionTypes(includeArchived: $includeArchived) {
        id name priority createdAt archivedAt
    }
}
"""

DIMENSION_TYPES_WITH_DIMENSIONS = """
query DimensionTypes {
    dimensionTypes {
        id name
        dimensions { edges { node { id name } } }
    }
}
"""

# ---------------------------------------------------------------------------
# Dimension GQL
# ---------------------------------------------------------------------------

CREATE_DIMENSION = """
mutation CreateDimension($input: CreateDimensionInput!) {
    createDimension(input: $input) {
        id type { id name } name description base createdAt updatedAt archivedAt
    }
}
"""

UPDATE_DIMENSION = """
mutation UpdateDimension($input: UpdateDimensionInput!) {
    updateDimension(input: $input) {
        id type { id name } name description base createdAt updatedAt archivedAt
    }
}
"""

ARCHIVE_DIMENSION = """
mutation ArchiveDimension($id: ID!) {
    archiveDimension(id: $id) {
        id name archivedAt
    }
}
"""

UNARCHIVE_DIMENSION = """
mutation UnarchiveDimension($id: ID!) {
    unarchiveDimension(id: $id) {
        id name archivedAt
    }
}
"""

DIMENSIONS = """
query Dimensions($typeId: ID!, $includeBase: Boolean, $includeArchived: Boolean, $first: Int, $after: String, $search: String) {
    dimensions(typeId: $typeId, includeBase: $includeBase, includeArchived: $includeArchived, first: $first, after: $after, search: $search) {
        edges {
            node { id type { id } name description base createdAt updatedAt archivedAt }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

DIMENSIONS_BY_IDS = """
query DimensionsByIds($ids: [ID!]!) {
    dimensionsByIds(ids: $ids) {
        id type { id name } name description base createdAt updatedAt archivedAt
    }
}
"""

DIMENSION_TYPES_WITH_DIMENSIONS_FILTERED = """
query DimensionTypesWithDimensionsFiltered($includeBase: Boolean, $includeArchived: Boolean, $search: String, $first: Int, $after: String) {
    dimensionTypes {
        id
        name
        dimensions(includeBase: $includeBase, includeArchived: $includeArchived, search: $search, first: $first, after: $after) {
            edges {
                node { id name base archivedAt }
            }
            pageInfo { hasNextPage endCursor }
        }
    }
}
"""

DIMENSION_TYPES_WITH_DIMENSIONS_NESTED = """
query DimensionTypesWithDimensions {
    dimensionTypes {
        id
        name
        dimensions {
            edges {
                node { id name base }
            }
        }
    }
}
"""

# ---------------------------------------------------------------------------
# Shared Value GQL
# ---------------------------------------------------------------------------

CREATE_SHARED_VALUE = """
mutation CreateSharedValue($input: CreateSharedValueInput!) {
    createSharedValue(input: $input) {
        id name createdAt updatedAt archivedAt
    }
}
"""

UPDATE_SHARED_VALUE = """
mutation UpdateSharedValue($input: UpdateSharedValueInput!) {
    updateSharedValue(input: $input) {
        id name createdAt updatedAt archivedAt
    }
}
"""

ARCHIVE_SHARED_VALUE = """
mutation ArchiveSharedValue($id: ID!) {
    archiveSharedValue(id: $id) {
        id name archivedAt
    }
}
"""

UNARCHIVE_SHARED_VALUE = """
mutation UnarchiveSharedValue($id: ID!) {
    unarchiveSharedValue(id: $id) {
        id name archivedAt
    }
}
"""

SHARED_VALUES = """
query SharedValues($includeArchived: Boolean, $first: Int, $after: String) {
    sharedValues(includeArchived: $includeArchived, first: $first, after: $after) {
        edges {
            node { id name createdAt updatedAt archivedAt }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

SHARED_VALUES_WITH_SEARCH = """
query SharedValuesWithSearch($search: String, $includeArchived: Boolean, $first: Int, $after: String) {
    sharedValues(search: $search, includeArchived: $includeArchived, first: $first, after: $after) {
        edges {
            node { id name createdAt updatedAt archivedAt }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

SHARED_VALUES_BY_IDS = """
query SharedValuesByIds($ids: [ID!]!) {
    sharedValuesByIds(ids: $ids) {
        id name createdAt updatedAt archivedAt
    }
}
"""

SHARED_VALUE_WITH_REVISIONS = """
query SharedValueWithRevisions(
    $ids: [ID!]!,
    $dimensionIds: [ID!],
    $currentOnly: Boolean,
    $first: Int,
    $after: String
) {
    sharedValuesByIds(ids: $ids) {
        id name
        revisions(
            dimensionIds: $dimensionIds,
            currentOnly: $currentOnly,
            first: $first,
            after: $after
        ) {
            edges {
                node { id sharedValue { id } dimensions { id name } value isCurrent createdAt }
                cursor
            }
            pageInfo { hasNextPage endCursor }
        }
    }
}
"""

# ---------------------------------------------------------------------------
# Shared Value Revision GQL
# ---------------------------------------------------------------------------

CREATE_REVISION = """
mutation CreateSharedValueRevision($input: CreateSharedValueRevisionInput!) {
    createSharedValueRevision(input: $input) {
        id sharedValue { id } dimensions { id name } value isCurrent createdAt
    }
}
"""

# ---------------------------------------------------------------------------
# Configuration GQL
# ---------------------------------------------------------------------------

CREATE_CONFIGURATION = """
mutation CreateConfiguration($input: CreateConfigurationInput!) {
    createConfiguration(input: $input) {
        id
        dimensions { id name }
        body
        isCurrent
        createdAt
        substitutions {
            id jsonpath sharedValue { id name } createdAt
        }
    }
}
"""

UPDATE_CONFIG_SUBSTITUTION = """
mutation UpdateConfigSubstitution($input: SetConfigSubstitutionInput!) {
    updateConfigSubstitution(input: $input) {
        id
        configuration { id }
        jsonpath
        sharedValue { id name }
        createdAt
    }
}
"""

CONFIGURATIONS = """
query Configurations($dimensionIds: [ID!], $includeBase: Boolean, $first: Int, $after: String) {
    configurations(dimensionIds: $dimensionIds, includeBase: $includeBase, first: $first, after: $after) {
        edges {
            node {
                id
                dimensions { id name }
                body
                isCurrent
                createdAt
                substitutions {
                    id jsonpath sharedValue { id }
                }
            }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

CONFIGURATIONS_BY_IDS = """
query ConfigurationsByIds($ids: [ID!]!) {
    configurationsByIds(ids: $ids) {
        id
        dimensions { id name }
        body
        isCurrent
        createdAt
    }
}
"""

CONFIGURATION_WITH_TYPED_DIMENSIONS = """
query ConfigurationWithTypedDimensions($ids: [ID!]!) {
    configurationsByIds(ids: $ids) {
        id
        dimensions { id name type { id name } }
        substitutions {
            id jsonpath
            configuration { id }
            sharedValue { id name }
        }
    }
}
"""

CONFIGURATION_WITH_PROJECTION = """
query ConfigurationWithProjection($ids: [ID!]!) {
    configurationsByIds(ids: $ids) {
        id
        body
        projection
    }
}
"""

SET_CONFIGURATION_CURRENT = """
mutation SetConfigurationCurrent($id: ID!, $isCurrent: Boolean!) {
    setConfigurationCurrent(id: $id, isCurrent: $isCurrent) {
        id body isCurrent
    }
}
"""

# ---------------------------------------------------------------------------
# Shared Value Revision extra GQL
# ---------------------------------------------------------------------------

SHARED_VALUE_WITH_REVISIONS_INCLUDE_BASE = """
query SharedValueWithRevisionsIncludeBase(
    $ids: [ID!]!,
    $dimensionIds: [ID!],
    $includeBase: Boolean,
    $currentOnly: Boolean,
    $first: Int,
    $after: String
) {
    sharedValuesByIds(ids: $ids) {
        id name
        revisions(
            dimensionIds: $dimensionIds,
            includeBase: $includeBase,
            currentOnly: $currentOnly,
            first: $first,
            after: $after
        ) {
            edges {
                node { id sharedValue { id } dimensions { id name } value isCurrent createdAt }
                cursor
            }
            pageInfo { hasNextPage endCursor }
        }
    }
}
"""

REVISION_WITH_TYPED_DIMENSIONS = """
query SharedValueWithRevisions($ids: [ID!]!) {
    sharedValuesByIds(ids: $ids) {
        id name
        revisions {
            edges {
                node {
                    id value isCurrent
                    sharedValue { id name }
                    dimensions { id name type { id name } }
                }
            }
        }
    }
}
"""

SET_REVISION_CURRENT = """
mutation SetRevisionCurrent($id: ID!, $isCurrent: Boolean!) {
    setRevisionCurrent(id: $id, isCurrent: $isCurrent) {
        id value isCurrent
    }
}
"""

# ---------------------------------------------------------------------------
# Shared Value usedBy GQL
# ---------------------------------------------------------------------------

SHARED_VALUE_USED_BY = """
query SharedValueUsedBy($ids: [ID!]!, $includeArchived: Boolean, $first: Int, $after: String) {
    sharedValuesByIds(ids: $ids) {
        id name
        usedBy(includeArchived: $includeArchived, first: $first, after: $after) {
            edges {
                node {
                    id body isCurrent
                    substitutions { id jsonpath sharedValue { id } }
                }
                cursor
            }
            pageInfo { hasNextPage endCursor }
        }
    }
}
"""

# ---------------------------------------------------------------------------
# Resolve Shared Value GQL
# ---------------------------------------------------------------------------

RESOLVE_SHARED_VALUE = """
query ResolveSharedValue($sharedValueId: ID!, $dimensionIds: [ID!]!) {
    resolveSharedValue(sharedValueId: $sharedValueId, dimensionIds: $dimensionIds) {
        id sharedValue { id } dimensions { id name } value isCurrent createdAt
    }
}
"""

CREATE_SHARED_VALUE_REVISION = """
mutation CreateSharedValueRevisionSlim($input: CreateSharedValueRevisionInput!) {
    createSharedValueRevision(input: $input) {
        id value isCurrent
        dimensions { id name }
    }
}
"""

CREATE_CONFIGURATION_FOR_LOADER = """
mutation CreateConfigurationForLoader($input: CreateConfigurationInput!) {
    createConfiguration(input: $input) {
        id body isCurrent
        substitutions { id jsonpath sharedValue { id } }
    }
}
"""

SHARED_VALUES_BY_IDS_WITH_USED_BY = """
query SharedValuesByIdsWithUsedBy($ids: [ID!]!) {
    sharedValuesByIds(ids: $ids) {
        id name
        usedBy {
            edges {
                node { id isCurrent }
            }
            pageInfo { hasNextPage endCursor }
        }
    }
}
"""

# ---------------------------------------------------------------------------
# Output GQL
# ---------------------------------------------------------------------------

CREATE_OUTPUT = """
mutation CreateOutput($input: CreateOutputInput!) {
    createOutput(input: $input) {
        id
        pathTemplate
        format
        dimensions { id name }
        results { id path content succeeded error }
        createdAt
        updatedAt
        archivedAt
    }
}
"""

TRIGGER_OUTPUT = """
mutation TriggerOutput($id: ID!) {
    triggerOutput(id: $id) {
        id
        pathTemplate
        format
        results {
            id
            path
            content
            succeeded
            error
        }
    }
}
"""

ARCHIVE_OUTPUT = """
mutation ArchiveOutput($id: ID!) {
    archiveOutput(id: $id) {
        id
        archivedAt
    }
}
"""

OUTPUTS_QUERY = """
query Outputs($includeArchived: Boolean, $first: Int, $after: String) {
    outputs(includeArchived: $includeArchived, first: $first, after: $after) {
        edges {
            node {
                id
                pathTemplate
                format
                archivedAt
            }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

OUTPUT_QUERY = """
query OutputsByIds($ids: [ID!]!) {
    outputsByIds(ids: $ids) {
        id
        pathTemplate
        format
        dimensions { id name }
        results {
            id
            path
            content
            succeeded
            error
        }
        archivedAt
    }
}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_type_id(client, type_name):
    body = await gql(client, GET_DIMENSION_TYPES)
    for dt in body["data"]["dimensionTypes"]:
        if dt["name"] == type_name:
            return dt["id"]
    raise ValueError(f"Dimension type '{type_name}' not found in seed data")


async def create_service(client, name="traefik", description=None):
    type_id = await _get_type_id(client, "service")
    return await create_dimension(client, type_id, name, description)


async def create_environment(client, name="production", description=None):
    type_id = await _get_type_id(client, "environment")
    return await create_dimension(client, type_id, name, description)


async def create_dimension_type(client, name):
    body = await gql(client, CREATE_DIMENSION_TYPE, {"input": {"name": name}})
    return body["data"]["createDimensionType"]


async def create_dimension(client, type_id, name, description=None):
    body = await gql(
        client,
        CREATE_DIMENSION,
        {"input": {"typeId": type_id, "name": name, "description": description}},
    )
    return body["data"]["createDimension"]


async def create_shared_value(client, name="db_password"):
    body = await gql(client, CREATE_SHARED_VALUE, {"input": {"name": name}})
    return body["data"]["createSharedValue"]


async def create_revision(client, shared_value_id, dimension_ids, value):
    body = await gql(
        client,
        CREATE_REVISION,
        {
            "input": {
                "sharedValueId": shared_value_id,
                "dimensionIds": dimension_ids,
                "value": value,
            }
        },
    )
    return body["data"]["createSharedValueRevision"]


async def create_configuration(client, dimension_ids, body, substitutions=None):
    """Create a configuration via GraphQL. Returns the full superset field shape."""
    variables = {
        "input": {
            "dimensionIds": dimension_ids,
            "body": body,
        }
    }
    if substitutions:
        variables["input"]["substitutions"] = substitutions
    result = await gql(client, CREATE_CONFIGURATION, variables)
    return result["data"]["createConfiguration"]


async def create_output(client, path_template, fmt, dimension_ids):
    """Create an output via GraphQL."""
    body = await gql(
        client,
        CREATE_OUTPUT,
        {
            "input": {
                "pathTemplate": path_template,
                "format": fmt,
                "dimensionIds": dimension_ids,
            }
        },
    )
    return body["data"]["createOutput"]


async def _create_service_dim(pool):
    """Create a service dimension directly via the pool and return its id."""
    row = await pool.fetchrow(
        """
        INSERT INTO dimensions (type_id, name)
        SELECT dt.id, 'svc-test'
        FROM dimension_types dt
        WHERE dt.name = 'service'
        RETURNING id
        """
    )
    return str(row["id"])


async def _create_env_dim(pool):
    """Create an environment dimension directly via the pool and return its id."""
    row = await pool.fetchrow(
        """
        INSERT INTO dimensions (type_id, name)
        SELECT dt.id, 'env-test'
        FROM dimension_types dt
        WHERE dt.name = 'environment'
        RETURNING id
        """
    )
    return str(row["id"])


async def trigger_output(client, output_id):
    """Trigger an output and return the trigger result dict."""
    body = await gql(client, TRIGGER_OUTPUT, {"id": output_id})
    return body["data"]["triggerOutput"]
