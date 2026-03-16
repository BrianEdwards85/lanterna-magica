from assertpy import assert_that
from conftest import gql
from gql import (
    CONFIGURATIONS,
    CONFIGURATIONS_BY_IDS,
    create_configuration,
    create_environment,
    create_service,
    create_shared_value,
)
from utils import nodes

from lanterna_magica.data.configurations import Configurations

# -- Configuration CRUD Tests --


async def test_create_configuration(client):
    svc = await create_service(client)
    env = await create_environment(client)
    config_body = {"host": "localhost", "port": 8080}

    cfg = await create_configuration(client, [svc["id"], env["id"]], config_body)
    assert_that(cfg["id"]).described_as("configuration id").is_not_none()
    assert_that(cfg["body"]).described_as("configuration body").is_equal_to(config_body)
    assert_that(cfg["isCurrent"]).described_as("new configuration is current").is_true()
    dim_ids = [d["id"] for d in cfg["dimensions"]]
    assert_that(dim_ids).described_as("dimension references").contains(
        svc["id"], env["id"]
    )
    assert_that(cfg["createdAt"]).described_as("createdAt timestamp").is_not_none()
    assert_that(cfg["substitutions"]).described_as("no substitutions").is_empty()


async def test_create_configuration_with_substitutions(client):
    svc = await create_service(client)
    env = await create_environment(client)
    sv = await create_shared_value(client, "db_password")

    config_body = {"database": {"password": "_"}}
    substitutions = [{"jsonpath": "$.database.password", "sharedValueId": sv["id"]}]

    cfg = await create_configuration(
        client, [svc["id"], env["id"]], config_body, substitutions
    )
    assert_that(cfg["substitutions"]).described_as("substitutions count").is_length(1)
    sub = cfg["substitutions"][0]
    assert_that(sub["jsonpath"]).described_as("substitution jsonpath").is_equal_to(
        "$.database.password"
    )
    assert_that(sub["sharedValue"]["id"]).described_as(
        "substitution shared value id"
    ).is_equal_to(sv["id"])


async def test_new_configuration_replaces_current(client):
    svc = await create_service(client)
    env = await create_environment(client)

    cfg1 = await create_configuration(client, [svc["id"], env["id"]], {"version": 1})
    cfg2 = await create_configuration(client, [svc["id"], env["id"]], {"version": 2})

    assert_that(cfg2["isCurrent"]).described_as("new config is current").is_true()

    # Check cfg1 is no longer current
    body = await gql(client, CONFIGURATIONS_BY_IDS, {"ids": [cfg1["id"]]})
    assert_that(body["data"]["configurationsByIds"][0]["isCurrent"]).described_as(
        "old config no longer current"
    ).is_false()


async def test_configuration_by_id(client):
    svc = await create_service(client)
    env = await create_environment(client)

    cfg = await create_configuration(client, [svc["id"], env["id"]], {"key": "value"})
    body = await gql(client, CONFIGURATIONS_BY_IDS, {"ids": [cfg["id"]]})
    found = body["data"]["configurationsByIds"][0]
    assert_that(found["id"]).described_as("fetched configuration id").is_equal_to(
        cfg["id"]
    )
    assert_that(found["body"]).described_as("fetched configuration body").is_equal_to(
        {"key": "value"}
    )


async def test_configuration_by_id_not_found(client):
    body = await gql(
        client, CONFIGURATIONS_BY_IDS, {"ids": ["00000000-0000-0000-0000-ffffffffffff"]}
    )
    assert_that(body["data"]["configurationsByIds"]).described_as(
        "non-existent id returns empty list"
    ).is_empty()


async def test_configurations_by_ids_fetches_multiple(client):
    svc = await create_service(client)
    env = await create_environment(client)

    cfg1 = await create_configuration(client, [svc["id"], env["id"]], {"version": 1})
    cfg2 = await create_configuration(client, [svc["id"], env["id"]], {"version": 2})

    body = await gql(client, CONFIGURATIONS_BY_IDS, {"ids": [cfg1["id"], cfg2["id"]]})
    results = body["data"]["configurationsByIds"]
    result_ids = [r["id"] for r in results]
    assert_that(results).described_as("fetches both configurations").is_length(2)
    assert_that(result_ids).described_as("returned ids match requested").contains(
        cfg1["id"], cfg2["id"]
    )


async def test_configurations_list(client):
    svc = await create_service(client)
    env = await create_environment(client)

    cfg1 = await create_configuration(client, [svc["id"], env["id"]], {"version": 1})
    cfg2 = await create_configuration(client, [svc["id"], env["id"]], {"version": 2})

    body = await gql(client, CONFIGURATIONS)
    items = nodes(body["data"]["configurations"]["edges"])
    assert_that(items).described_as("configurations list").extracting("id").contains(
        cfg1["id"], cfg2["id"]
    )


async def test_configurations_filter_by_dimension(client):
    svc1 = await create_service(client, "traefik")
    svc2 = await create_service(client, "nginx")
    env = await create_environment(client)

    await create_configuration(client, [svc1["id"], env["id"]], {"app": "traefik"})
    await create_configuration(client, [svc2["id"], env["id"]], {"app": "nginx"})

    body = await gql(client, CONFIGURATIONS, {"dimensionIds": [svc1["id"]]})
    items = nodes(body["data"]["configurations"]["edges"])
    assert_that(items).described_as("configs filtered by dimension").is_length(1)
    assert_that(items[0]["body"]).described_as("filtered config body").is_equal_to(
        {"app": "traefik"}
    )


async def test_configurations_pagination(client):
    svc = await create_service(client)
    env = await create_environment(client)

    for i in range(5):
        await create_configuration(client, [svc["id"], env["id"]], {"version": i})

    body = await gql(client, CONFIGURATIONS, {"first": 2})
    page1 = body["data"]["configurations"]
    assert_that(page1["edges"]).described_as("page 1 edge count").is_length(2)
    assert_that(page1["pageInfo"]["hasNextPage"]).described_as(
        "page 1 has next page"
    ).is_true()

    body = await gql(
        client, CONFIGURATIONS, {"first": 2, "after": page1["pageInfo"]["endCursor"]}
    )
    page2 = body["data"]["configurations"]
    assert_that(page2["edges"]).described_as("page 2 edge count").is_length(2)
    assert_that(page2["pageInfo"]["hasNextPage"]).described_as(
        "page 2 has next page"
    ).is_true()

    body = await gql(
        client, CONFIGURATIONS, {"first": 2, "after": page2["pageInfo"]["endCursor"]}
    )
    page3 = body["data"]["configurations"]
    assert_that(page3["edges"]).described_as("page 3 edge count").is_length(1)
    assert_that(page3["pageInfo"]["hasNextPage"]).described_as(
        "page 3 has no next page"
    ).is_false()


async def test_configuration_by_invalid_uuid(client):
    body = await gql(
        client, CONFIGURATIONS_BY_IDS, {"ids": ["not-a-uuid"]}, expect_errors=True
    )
    assert_that(body).described_as("invalid uuid rejected").contains_key("errors")


# -- Data-layer tests for Configurations.get_by_ids --


async def test_get_by_ids_multiple(client, pool):
    """get_by_ids returns multiple configurations by their IDs."""
    svc = await create_service(client)
    env = await create_environment(client)
    configs = Configurations(pool)

    cfg_a = await create_configuration(client, [svc["id"], env["id"]], {"tag": "a"})
    cfg_b = await create_configuration(client, [svc["id"], env["id"]], {"tag": "b"})
    cfg_c = await create_configuration(client, [svc["id"], env["id"]], {"tag": "c"})

    result = await configs.get_by_ids(ids=[cfg_a["id"], cfg_c["id"]])

    assert_that(result).described_as("returns two configurations").is_length(2)
    returned_ids = {str(r["id"]) for r in result}
    assert_that(returned_ids).described_as("correct ids returned").is_equal_to(
        {cfg_a["id"], cfg_c["id"]}
    )
    # b was not requested and should not be present
    assert_that(cfg_b["id"]).described_as("unrequested config absent").is_not_in(
        returned_ids
    )


async def test_get_by_ids_empty_list(pool):
    """get_by_ids returns an empty list when given no IDs."""
    configs = Configurations(pool)
    result = await configs.get_by_ids(ids=[])
    assert_that(result).described_as("empty list for empty ids").is_equal_to([])


async def test_get_by_ids_unknown_ids(pool):
    """get_by_ids returns an empty list when no IDs match."""
    configs = Configurations(pool)
    result = await configs.get_by_ids(ids=["00000000-0000-0000-0000-ffffffffffff"])
    assert_that(result).described_as("empty list for unknown ids").is_equal_to([])
