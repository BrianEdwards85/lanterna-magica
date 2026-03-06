from assertpy import assert_that


async def test_health_ok(client):
    resp = await client.get("/health")
    assert_that(resp.status_code).described_as("health status code").is_equal_to(200)
    assert_that(resp.json()["status"]).described_as("health status").is_equal_to("ok")
