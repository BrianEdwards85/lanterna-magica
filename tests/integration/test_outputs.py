import pytest
from assertpy import assert_that

from lanterna_magica.data.outputs import Outputs
from lanterna_magica.errors import NotFoundError

# -- Helpers --


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


# -- Tests --


async def test_create_output_with_dimensions(pool):
    """create embeds dimensions and returns output dict."""
    dim_id = await _create_service_dim(pool)
    outputs = Outputs(pool)

    result = await outputs.create(
        path_template="/etc/configs/{service}.json",
        format="json",
        dimension_ids=[dim_id],
    )

    assert_that(result["path_template"]).described_as("path_template").is_equal_to(
        "/etc/configs/{service}.json"
    )
    assert_that(result["format"]).described_as("format").is_equal_to("json")
    assert_that(result["id"]).described_as("id set").is_not_none()
    assert_that(result["archived_at"]).described_as("not archived").is_none()
    assert_that(result["dimensions"]).described_as("dimensions embedded").is_length(1)
    assert_that(str(result["dimensions"][0]["id"])).described_as(
        "dimension id matches"
    ).is_equal_to(dim_id)


async def test_create_output_no_dimensions(pool):
    """create works with an empty dimension_ids list."""
    outputs = Outputs(pool)
    result = await outputs.create(
        path_template="/etc/app.yml",
        format="yml",
        dimension_ids=[],
    )
    assert_that(result["format"]).is_equal_to("yml")
    assert_that(result["dimensions"]).described_as("no dimensions").is_length(0)


async def test_create_output_multiple_dimensions(pool):
    """create inserts multiple dimension rows and returns them all."""
    svc_id = await _create_service_dim(pool)
    env_id = await _create_env_dim(pool)
    outputs = Outputs(pool)

    result = await outputs.create(
        path_template="/etc/{service}/{env}.toml",
        format="toml",
        dimension_ids=[svc_id, env_id],
    )
    dim_ids = {str(d["id"]) for d in result["dimensions"]}
    assert_that(dim_ids).described_as("both dimensions embedded").is_equal_to(
        {svc_id, env_id}
    )


async def test_get_output(pool):
    """get returns the output by id."""
    outputs = Outputs(pool)
    created = await outputs.create(
        path_template="/tmp/out.env",
        format="env",
        dimension_ids=[],
    )
    fetched = await outputs.get(id=str(created["id"]))
    assert_that(fetched).described_as("found").is_not_none()
    assert_that(str(fetched["id"])).is_equal_to(str(created["id"]))
    assert_that(fetched["path_template"]).is_equal_to("/tmp/out.env")


async def test_get_output_not_found(pool):
    """get returns None for a non-existent id."""
    outputs = Outputs(pool)
    result = await outputs.get(id="00000000-0000-0000-0000-ffffffffffff")
    assert_that(result).described_as("not found returns None").is_none()


async def test_list_outputs_basic(pool):
    """list returns created outputs."""
    outputs = Outputs(pool)
    await outputs.create(path_template="/a.json", format="json", dimension_ids=[])
    await outputs.create(path_template="/b.json", format="json", dimension_ids=[])

    connection = await outputs.list(include_archived=False)
    templates = [e["node"]["path_template"] for e in connection["edges"]]
    assert_that(templates).described_as("both outputs listed").contains("/a.json", "/b.json")


async def test_list_outputs_excludes_archived_by_default(pool):
    """list excludes archived outputs when include_archived=False."""
    outputs = Outputs(pool)
    await outputs.create(path_template="/keep.json", format="json", dimension_ids=[])
    b = await outputs.create(path_template="/archive.json", format="json", dimension_ids=[])
    await outputs.archive(id=str(b["id"]))

    connection = await outputs.list(include_archived=False)
    templates = [e["node"]["path_template"] for e in connection["edges"]]
    assert_that(templates).described_as("archived not shown").contains("/keep.json")
    assert_that(templates).described_as("archived excluded").does_not_contain("/archive.json")


async def test_list_outputs_includes_archived(pool):
    """list includes archived outputs when include_archived=True."""
    outputs = Outputs(pool)
    await outputs.create(path_template="/keep.json", format="json", dimension_ids=[])
    b = await outputs.create(path_template="/archive.json", format="json", dimension_ids=[])
    await outputs.archive(id=str(b["id"]))

    connection = await outputs.list(include_archived=True)
    templates = [e["node"]["path_template"] for e in connection["edges"]]
    assert_that(templates).described_as("both shown with include_archived").contains(
        "/keep.json", "/archive.json"
    )


async def test_list_outputs_pagination(pool):
    """list supports cursor-based pagination."""
    outputs = Outputs(pool)
    for i in range(5):
        await outputs.create(path_template=f"/out-{i:02d}.json", format="json", dimension_ids=[])

    page1 = await outputs.list(first=2)
    assert_that(page1["edges"]).described_as("page 1 size").is_length(2)
    assert_that(page1["page_info"]["has_next_page"]).described_as("has next page").is_true()

    page2 = await outputs.list(first=2, after=page1["page_info"]["end_cursor"])
    assert_that(page2["edges"]).described_as("page 2 size").is_length(2)


async def test_archive_output(pool):
    """archive sets archived_at on the output."""
    outputs = Outputs(pool)
    created = await outputs.create(path_template="/x.json", format="json", dimension_ids=[])
    archived = await outputs.archive(id=str(created["id"]))

    assert_that(archived["archived_at"]).described_as("archived_at set").is_not_none()
    assert_that(str(archived["id"])).is_equal_to(str(created["id"]))


async def test_archive_output_not_found(pool):
    """archive raises NotFoundError for non-existent id."""
    outputs = Outputs(pool)
    with pytest.raises(NotFoundError):
        await outputs.archive(id="00000000-0000-0000-0000-ffffffffffff")


async def test_archive_output_already_archived(pool):
    """archive raises NotFoundError if output is already archived."""
    outputs = Outputs(pool)
    created = await outputs.create(path_template="/x.json", format="json", dimension_ids=[])
    await outputs.archive(id=str(created["id"]))

    with pytest.raises(NotFoundError):
        await outputs.archive(id=str(created["id"]))


async def test_get_dimensions(pool):
    """get_dimensions returns the dimensions for an output."""
    dim_id = await _create_service_dim(pool)
    outputs = Outputs(pool)
    created = await outputs.create(
        path_template="/z.json", format="json", dimension_ids=[dim_id]
    )

    dims = await outputs.get_dimensions(output_id=str(created["id"]))
    assert_that(dims).described_as("one dimension").is_length(1)
    assert_that(str(dims[0]["id"])).is_equal_to(dim_id)


async def test_upsert_result_insert(pool):
    """upsert_result inserts a new result row."""
    outputs = Outputs(pool)
    created = await outputs.create(path_template="/r.json", format="json", dimension_ids=[])

    result = await outputs.upsert_result(
        output_id=str(created["id"]),
        scope_hash="00000000-0000-0000-0000-000000000001",
        path="/tmp/r.json",
        content='{"key": "value"}',
        succeeded=True,
        error=None,
    )

    assert_that(result["path"]).is_equal_to("/tmp/r.json")
    assert_that(result["content"]).is_equal_to('{"key": "value"}')
    assert_that(result["succeeded"]).is_true()
    assert_that(result["error"]).is_none()
    assert_that(result["id"]).is_not_none()


async def test_upsert_result_update(pool):
    """upsert_result updates an existing result on conflict."""
    outputs = Outputs(pool)
    created = await outputs.create(path_template="/r.json", format="json", dimension_ids=[])
    scope_hash = "00000000-0000-0000-0000-000000000002"

    first = await outputs.upsert_result(
        output_id=str(created["id"]),
        scope_hash=scope_hash,
        path="/tmp/r.json",
        content='{"v": 1}',
        succeeded=True,
        error=None,
    )

    second = await outputs.upsert_result(
        output_id=str(created["id"]),
        scope_hash=scope_hash,
        path="/tmp/r-v2.json",
        content='{"v": 2}',
        succeeded=False,
        error="disk full",
    )

    assert_that(str(second["id"])).described_as("same row updated").is_equal_to(str(first["id"]))
    assert_that(second["path"]).is_equal_to("/tmp/r-v2.json")
    assert_that(second["content"]).is_equal_to('{"v": 2}')
    assert_that(second["succeeded"]).is_false()
    assert_that(second["error"]).is_equal_to("disk full")


async def test_get_results(pool):
    """get_results returns all results for an output ordered by path."""
    outputs = Outputs(pool)
    created = await outputs.create(path_template="/r.json", format="json", dimension_ids=[])

    await outputs.upsert_result(
        output_id=str(created["id"]),
        scope_hash="00000000-0000-0000-0000-000000000010",
        path="/b/r.json",
        content="{}",
        succeeded=True,
    )
    await outputs.upsert_result(
        output_id=str(created["id"]),
        scope_hash="00000000-0000-0000-0000-000000000011",
        path="/a/r.json",
        content="{}",
        succeeded=True,
    )

    results = await outputs.get_results(output_id=str(created["id"]))
    assert_that(results).described_as("two results").is_length(2)
    paths = [r["path"] for r in results]
    assert_that(paths).described_as("ordered by path asc").is_equal_to(
        ["/a/r.json", "/b/r.json"]
    )
