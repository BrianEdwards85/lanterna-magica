from assertpy import assert_that
from conftest import gql
from utils import create_environment, nodes, parse_dt

# -- Mutations --

CREATE_ENVIRONMENT = """
mutation CreateEnvironment($input: CreateEnvironmentInput!) {
    createEnvironment(input: $input) {
        id name description createdAt updatedAt archivedAt
    }
}
"""

UPDATE_ENVIRONMENT = """
mutation UpdateEnvironment($input: UpdateEnvironmentInput!) {
    updateEnvironment(input: $input) {
        id name description createdAt updatedAt archivedAt
    }
}
"""

ARCHIVE_ENVIRONMENT = """
mutation ArchiveEnvironment($id: ID!) {
    archiveEnvironment(id: $id) {
        id name archivedAt
    }
}
"""

UNARCHIVE_ENVIRONMENT = """
mutation UnarchiveEnvironment($id: ID!) {
    unarchiveEnvironment(id: $id) {
        id name archivedAt
    }
}
"""

# -- Queries --

ENVIRONMENTS = """
query Environments($includeArchived: Boolean, $first: Int, $after: String, $search: String) {
    environments(includeArchived: $includeArchived, first: $first, after: $after, search: $search) {
        edges {
            node { id name description createdAt updatedAt archivedAt }
            cursor
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""

ENVIRONMENT = """
query Environment($id: ID!) {
    environment(id: $id) {
        id name description createdAt updatedAt archivedAt
    }
}
"""


# -- Tests --


async def test_create_environment(client):
    env = await create_environment(client, "production", "prod cluster")
    assert_that(env["name"]).described_as("environment name").is_equal_to("production")
    assert_that(env["description"]).described_as("environment description").is_equal_to(
        "prod cluster"
    )
    assert_that(env["id"]).described_as("environment id").is_not_none()
    assert_that(env["createdAt"]).described_as("createdAt timestamp").is_not_none()
    assert_that(env["updatedAt"]).described_as("updatedAt timestamp").is_not_none()
    assert_that(env["archivedAt"]).described_as(
        "new environment should not be archived"
    ).is_none()


async def test_create_environment_minimal(client):
    env = await create_environment(client, "staging")
    assert_that(env["name"]).described_as("environment name").is_equal_to("staging")
    assert_that(env["description"]).described_as("description when not provided").is_none()


async def test_create_environment_duplicate_name(client):
    await create_environment(client, "production")
    body = await gql(
        client,
        CREATE_ENVIRONMENT,
        {"input": {"name": "production"}},
        expect_errors=True,
    )
    assert_that(body).described_as("duplicate name should return errors").contains_key("errors")


async def test_environment_by_id(client):
    env = await create_environment(client)
    body = await gql(client, ENVIRONMENT, {"id": env["id"]})
    found = body["data"]["environment"]
    assert_that(found["id"]).described_as("fetched environment id").is_equal_to(env["id"])
    assert_that(found["name"]).described_as("fetched environment name").is_equal_to(env["name"])


async def test_environment_by_id_not_found(client):
    body = await gql(client, ENVIRONMENT, {"id": "00000000-0000-0000-0000-ffffffffffff"})
    assert_that(body["data"]["environment"]).described_as("non-existent id").is_none()


async def test_environments_list(client):
    await create_environment(client, "production")
    await create_environment(client, "staging")

    body = await gql(client, ENVIRONMENTS)
    assert_that(nodes(body["data"]["environments"]["edges"])).described_as(
        "environments list"
    ).extracting("name").contains("production", "staging")


async def test_environments_excludes_sentinel(client):
    body = await gql(client, ENVIRONMENTS)
    assert_that(nodes(body["data"]["environments"]["edges"])).described_as(
        "sentinel row should be hidden"
    ).extracting("name").does_not_contain("_global")


async def test_update_environment(client):
    env = await create_environment(client, "production")

    body = await gql(
        client,
        UPDATE_ENVIRONMENT,
        {"input": {"id": env["id"], "description": "prod cluster"}},
    )
    updated = body["data"]["updateEnvironment"]
    assert_that(updated["name"]).described_as("name unchanged").is_equal_to("production")
    assert_that(updated["description"]).described_as("description updated").is_equal_to(
        "prod cluster"
    )
    assert_that(parse_dt(updated["updatedAt"])).described_as("updatedAt advanced").is_after(
        parse_dt(env["updatedAt"])
    )


async def test_update_environment_partial(client):
    env = await create_environment(client, "production", "original description")

    body = await gql(
        client,
        UPDATE_ENVIRONMENT,
        {"input": {"id": env["id"], "name": "prod"}},
    )
    updated = body["data"]["updateEnvironment"]
    assert_that(updated["name"]).described_as("name updated").is_equal_to("prod")
    assert_that(updated["description"]).described_as("description preserved").is_equal_to(
        "original description"
    )


async def test_update_environment_no_fields_fails(client):
    env = await create_environment(client)
    body = await gql(
        client,
        UPDATE_ENVIRONMENT,
        {"input": {"id": env["id"]}},
        expect_errors=True,
    )
    assert_that(body).described_as("no-op update rejected").contains_key("errors")


async def test_update_archived_environment_fails(client):
    env = await create_environment(client)
    await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})

    body = await gql(
        client,
        UPDATE_ENVIRONMENT,
        {"input": {"id": env["id"], "name": "new-name"}},
        expect_errors=True,
    )
    assert_that(body).described_as("updating archived environment").contains_key("errors")


async def test_archive_environment(client):
    env = await create_environment(client)

    body = await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})
    archived = body["data"]["archiveEnvironment"]
    assert_that(archived["archivedAt"]).described_as("archivedAt should be set").is_not_none()


async def test_archive_hides_from_list(client):
    env = await create_environment(client)
    await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})

    body = await gql(client, ENVIRONMENTS)
    assert_that(nodes(body["data"]["environments"]["edges"])).described_as(
        "archived environment hidden from default list"
    ).extracting("id").does_not_contain(env["id"])


async def test_include_archived(client):
    env = await create_environment(client)
    await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})

    body = await gql(client, ENVIRONMENTS, {"includeArchived": True})
    assert_that(nodes(body["data"]["environments"]["edges"])).described_as(
        "archived environment visible with includeArchived"
    ).extracting("id").contains(env["id"])


async def test_unarchive_environment(client):
    env = await create_environment(client)
    await gql(client, ARCHIVE_ENVIRONMENT, {"id": env["id"]})

    body = await gql(client, UNARCHIVE_ENVIRONMENT, {"id": env["id"]})
    restored = body["data"]["unarchiveEnvironment"]
    assert_that(restored["archivedAt"]).described_as(
        "archivedAt cleared after unarchive"
    ).is_none()

    body = await gql(client, ENVIRONMENTS)
    assert_that(nodes(body["data"]["environments"]["edges"])).described_as(
        "unarchived environment visible in default list"
    ).extracting("id").contains(env["id"])


async def test_search_by_name(client):
    await create_environment(client, "production", "prod cluster")
    await create_environment(client, "staging", "staging cluster")

    body = await gql(client, ENVIRONMENTS, {"search": "production"})
    edges = body["data"]["environments"]["edges"]
    assert_that(edges).described_as("search by name result count").is_length(1)
    assert_that(edges[0]["node"]["name"]).described_as("matched environment name").is_equal_to(
        "production"
    )


async def test_search_by_description(client):
    await create_environment(client, "production", "prod cluster")
    await create_environment(client, "staging", "test environment")

    body = await gql(client, ENVIRONMENTS, {"search": "test environment"})
    edges = body["data"]["environments"]["edges"]
    assert_that(edges).described_as("search by description result count").is_length(1)
    assert_that(edges[0]["node"]["name"]).described_as("matched environment name").is_equal_to(
        "staging"
    )


async def test_search_case_insensitive(client):
    await create_environment(client, "Production")

    body = await gql(client, ENVIRONMENTS, {"search": "production"})
    edges = body["data"]["environments"]["edges"]
    assert_that(edges).described_as("case-insensitive search result count").is_length(1)


async def test_pagination(client):
    for i in range(5):
        await create_environment(client, f"env-{i:02d}")

    body = await gql(client, ENVIRONMENTS, {"first": 2})
    page1 = body["data"]["environments"]
    assert_that(page1["edges"]).described_as("page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as("page 1 has next page").is_true()

    body = await gql(client, ENVIRONMENTS, {"first": 2, "after": page1["pageInfo"]["endCursor"]})
    page2 = body["data"]["environments"]
    assert_that(page2["edges"]).described_as("page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as("page 2 has next page").is_true()

    body = await gql(client, ENVIRONMENTS, {"first": 2, "after": page2["pageInfo"]["endCursor"]})
    page3 = body["data"]["environments"]
    assert_that(page3["edges"]).described_as("page 3 edge count").is_length(1)
    assert_that(page3["pageInfo"]["hasNextPage"]).described_as(
        "page 3 has no next page"
    ).is_false()


async def test_pagination_with_search(client):
    for i in range(4):
        await create_environment(client, f"alpha-{i:02d}")
    await create_environment(client, "beta-00")

    body = await gql(client, ENVIRONMENTS, {"search": "alpha", "first": 2})
    page1 = body["data"]["environments"]
    assert_that(page1["edges"]).described_as("search page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as(
        "search page 1 has next page"
    ).is_true()

    body = await gql(
        client,
        ENVIRONMENTS,
        {"search": "alpha", "first": 2, "after": page1["pageInfo"]["endCursor"]},
    )
    page2 = body["data"]["environments"]
    assert_that(page2["edges"]).described_as("search page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as(
        "search page 2 has no next page"
    ).is_false()


async def test_cursor_invalid_with_changed_search(client):
    for i in range(3):
        await create_environment(client, f"env-{i:02d}")

    body = await gql(client, ENVIRONMENTS, {"search": "env", "first": 1})
    cursor = body["data"]["environments"]["pageInfo"]["endCursor"]

    body = await gql(
        client,
        ENVIRONMENTS,
        {"search": "other", "first": 1, "after": cursor},
        expect_errors=True,
    )
    assert_that(body).described_as("mismatched search cursor").contains_key("errors")


async def test_create_environment_with_percent_in_name_fails(client):
    body = await gql(
        client, CREATE_ENVIRONMENT, {"input": {"name": "bad%name"}}, expect_errors=True
    )
    assert_that(body).described_as("percent in name rejected").contains_key("errors")


async def test_create_environment_with_backslash_in_name_fails(client):
    body = await gql(
        client, CREATE_ENVIRONMENT, {"input": {"name": "bad\\name"}}, expect_errors=True
    )
    assert_that(body).described_as("backslash in name rejected").contains_key("errors")


async def test_update_environment_with_percent_in_name_fails(client):
    env = await create_environment(client)
    body = await gql(
        client,
        UPDATE_ENVIRONMENT,
        {"input": {"id": env["id"], "name": "bad%name"}},
        expect_errors=True,
    )
    assert_that(body).described_as("percent in update name rejected").contains_key("errors")


async def test_environment_name_with_underscore_allowed(client):
    env = await create_environment(client, "my_env")
    assert_that(env["name"]).described_as("underscore in name").is_equal_to("my_env")


async def test_search_underscore_literal(client):
    await create_environment(client, "my_env")
    await create_environment(client, "myXenv")

    body = await gql(client, ENVIRONMENTS, {"search": "_"})
    edges = body["data"]["environments"]["edges"]
    assert_that(edges).described_as("underscore search matches only literal _").is_length(1)
    assert_that(edges[0]["node"]["name"]).is_equal_to("my_env")


async def test_search_strips_invalid_chars(client):
    await create_environment(client, "production")

    body = await gql(client, ENVIRONMENTS, {"search": "%production"})
    edges = body["data"]["environments"]["edges"]
    assert_that(edges).described_as("search with stripped % still finds result").is_length(1)
    assert_that(edges[0]["node"]["name"]).is_equal_to("production")
