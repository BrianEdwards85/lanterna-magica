from assertpy import assert_that


async def test_health_ok(client):
    resp = await client.get("/health")
    assert_that(resp.status_code).described_as("health status code").is_equal_to(200)
    body = resp.json()
    assert_that(body["status"]).described_as("health status").is_equal_to("healthy")
    assert_that(body["checks"]["db"]).described_as("db check").is_equal_to("ok")
