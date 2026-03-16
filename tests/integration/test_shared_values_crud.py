from assertpy import assert_that
from conftest import gql
from gql import (
    ARCHIVE_SHARED_VALUE,
    CREATE_SHARED_VALUE,
    SHARED_VALUES,
    SHARED_VALUES_BY_IDS,
    SHARED_VALUES_WITH_SEARCH,
    UNARCHIVE_SHARED_VALUE,
    UPDATE_SHARED_VALUE,
    create_shared_value,
)
from utils import nodes, parse_dt

# -- Shared Value CRUD Tests --


async def test_create_shared_value(client):
    sv = await create_shared_value(client, "db_password")
    assert_that(sv["name"]).described_as("shared value name").is_equal_to("db_password")
    assert_that(sv["id"]).described_as("shared value id").is_not_none()
    assert_that(sv["createdAt"]).described_as("createdAt timestamp").is_not_none()
    assert_that(sv["archivedAt"]).described_as(
        "new shared value should not be archived"
    ).is_none()


async def test_create_shared_value_duplicate_name(client):
    await create_shared_value(client, "db_password")
    body = await gql(
        client,
        CREATE_SHARED_VALUE,
        {"input": {"name": "db_password"}},
        expect_errors=True,
    )
    assert_that(body).described_as("duplicate name should return errors").contains_key(
        "errors"
    )


async def test_shared_values_by_ids(client):
    sv = await create_shared_value(client)
    body = await gql(client, SHARED_VALUES_BY_IDS, {"ids": [sv["id"]]})
    results = body["data"]["sharedValuesByIds"]
    assert_that(results).described_as("returns one result").is_length(1)
    found = results[0]
    assert_that(found["id"]).described_as("fetched shared value id").is_equal_to(
        sv["id"]
    )
    assert_that(found["name"]).described_as("fetched shared value name").is_equal_to(
        sv["name"]
    )


async def test_shared_values_by_ids_multiple(client):
    sv1 = await create_shared_value(client, "db_password")
    sv2 = await create_shared_value(client, "api_key")

    body = await gql(client, SHARED_VALUES_BY_IDS, {"ids": [sv1["id"], sv2["id"]]})
    found = body["data"]["sharedValuesByIds"]
    assert_that(found).described_as("fetched shared values count").is_length(2)
    ids = [sv["id"] for sv in found]
    assert_that(ids).described_as("fetched shared value ids").contains(
        sv1["id"], sv2["id"]
    )


async def test_shared_values_by_ids_unknown_returns_empty(client):
    body = await gql(
        client, SHARED_VALUES_BY_IDS, {"ids": ["00000000-0000-0000-0000-ffffffffffff"]}
    )
    assert_that(body["data"]["sharedValuesByIds"]).described_as(
        "non-existent id returns empty list"
    ).is_empty()


async def test_shared_values_list(client):
    await create_shared_value(client, "db_password")
    await create_shared_value(client, "api_key")

    body = await gql(client, SHARED_VALUES)
    assert_that(nodes(body["data"]["sharedValues"]["edges"])).described_as(
        "shared values list"
    ).extracting("name").contains("db_password", "api_key")


async def test_update_shared_value(client):
    sv = await create_shared_value(client, "db_password")

    body = await gql(
        client,
        UPDATE_SHARED_VALUE,
        {"input": {"id": sv["id"], "name": "db_pass"}},
    )
    updated = body["data"]["updateSharedValue"]
    assert_that(updated["name"]).described_as("name updated").is_equal_to("db_pass")
    assert_that(parse_dt(updated["updatedAt"])).described_as(
        "updatedAt advanced"
    ).is_after(parse_dt(sv["updatedAt"]))


async def test_update_shared_value_no_fields_fails(client):
    sv = await create_shared_value(client)
    body = await gql(
        client,
        UPDATE_SHARED_VALUE,
        {"input": {"id": sv["id"]}},
        expect_errors=True,
    )
    assert_that(body).described_as("no-op update rejected").contains_key("errors")


async def test_update_archived_shared_value_fails(client):
    sv = await create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(
        client,
        UPDATE_SHARED_VALUE,
        {"input": {"id": sv["id"], "name": "new_name"}},
        expect_errors=True,
    )
    assert_that(body).described_as("updating archived shared value").contains_key(
        "errors"
    )


async def test_archive_shared_value(client):
    sv = await create_shared_value(client)

    body = await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})
    archived = body["data"]["archiveSharedValue"]
    assert_that(archived["archivedAt"]).described_as(
        "archivedAt should be set"
    ).is_not_none()


async def test_archive_hides_from_list(client):
    sv = await create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(client, SHARED_VALUES)
    assert_that(nodes(body["data"]["sharedValues"]["edges"])).described_as(
        "archived shared value hidden from default list"
    ).extracting("id").does_not_contain(sv["id"])


async def test_include_archived(client):
    sv = await create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(client, SHARED_VALUES, {"includeArchived": True})
    assert_that(nodes(body["data"]["sharedValues"]["edges"])).described_as(
        "archived shared value visible with includeArchived"
    ).extracting("id").contains(sv["id"])


async def test_unarchive_shared_value(client):
    sv = await create_shared_value(client)
    await gql(client, ARCHIVE_SHARED_VALUE, {"id": sv["id"]})

    body = await gql(client, UNARCHIVE_SHARED_VALUE, {"id": sv["id"]})
    restored = body["data"]["unarchiveSharedValue"]
    assert_that(restored["archivedAt"]).described_as(
        "archivedAt cleared after unarchive"
    ).is_none()

    body = await gql(client, SHARED_VALUES)
    assert_that(nodes(body["data"]["sharedValues"]["edges"])).described_as(
        "unarchived shared value visible in default list"
    ).extracting("id").contains(sv["id"])


async def test_search_by_name(client):
    await create_shared_value(client, "db_password")
    await create_shared_value(client, "api_key")

    body = await gql(client, SHARED_VALUES_WITH_SEARCH, {"search": "db_pass"})
    results = nodes(body["data"]["sharedValues"]["edges"])
    assert_that(results).described_as("search by name result count").is_length(1)
    assert_that(results[0]["name"]).described_as(
        "matched shared value name"
    ).is_equal_to("db_password")


async def test_search_respects_pagination(client):
    """Search should respect first/after pagination."""
    for i in range(5):
        await create_shared_value(client, f"db_val_{i:02d}")
    await create_shared_value(client, "api_key")

    body = await gql(
        client, SHARED_VALUES_WITH_SEARCH, {"search": "db_val", "first": 3}
    )
    page = body["data"]["sharedValues"]
    results = nodes(page["edges"])
    assert_that(results).described_as("search limited to first").is_length(3)
    assert_that(page["pageInfo"]["hasNextPage"]).described_as(
        "more search results available"
    ).is_true()


async def test_pagination(client):
    for i in range(5):
        await create_shared_value(client, f"val-{i:02d}")

    body = await gql(client, SHARED_VALUES, {"first": 2})
    page1 = body["data"]["sharedValues"]
    assert_that(page1["edges"]).described_as("page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as(
        "page 1 has next page"
    ).is_true()

    body = await gql(
        client, SHARED_VALUES, {"first": 2, "after": page1["pageInfo"]["endCursor"]}
    )
    page2 = body["data"]["sharedValues"]
    assert_that(page2["edges"]).described_as("page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as(
        "page 2 has next page"
    ).is_true()

    body = await gql(
        client, SHARED_VALUES, {"first": 2, "after": page2["pageInfo"]["endCursor"]}
    )
    page3 = body["data"]["sharedValues"]
    assert_that(page3["edges"]).described_as("page 3 edge count").is_length(1)
    assert_that(page3["pageInfo"]["hasNextPage"]).described_as(
        "page 3 has no next page"
    ).is_false()


async def test_update_shared_value_with_percent_in_name_fails(client):
    sv = await create_shared_value(client)
    body = await gql(
        client,
        UPDATE_SHARED_VALUE,
        {"input": {"id": sv["id"], "name": "bad%name"}},
        expect_errors=True,
    )
    assert_that(body).described_as("percent in update name rejected").contains_key(
        "errors"
    )


async def test_shared_value_name_with_underscore_allowed(client):
    sv = await create_shared_value(client, "my_value")
    assert_that(sv["name"]).described_as("underscore in name").is_equal_to("my_value")
