import pytest
from assertpy import assert_that
from gql import _create_env_dim, _create_service_dim

from lanterna_magica.data.outputs import Outputs
from lanterna_magica.errors import NotFoundError

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

    assert_that(result["path_template"]).described_as("path_template").is_equal_to("/etc/configs/{service}.json")
    assert_that(result["format"]).described_as("format").is_equal_to("json")
    assert_that(result["id"]).described_as("id set").is_not_none()
    assert_that(result["archived_at"]).described_as("not archived").is_none()
    assert_that(result["dimensions"]).described_as("dimensions embedded").is_length(1)
    assert_that(str(result["dimensions"][0]["id"])).described_as("dimension id matches").is_equal_to(dim_id)


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
    assert_that(dim_ids).described_as("both dimensions embedded").is_equal_to({svc_id, env_id})


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


async def test_get_by_ids_multiple(pool):
    """get_by_ids returns multiple outputs by their IDs."""
    outputs = Outputs(pool)
    a = await outputs.create(path_template="/a.json", format="json", dimension_ids=[])
    b = await outputs.create(path_template="/b.json", format="json", dimension_ids=[])
    c = await outputs.create(path_template="/c.json", format="json", dimension_ids=[])

    result = await outputs.get_by_ids(ids=[str(a["id"]), str(c["id"])])

    assert_that(result).described_as("returns two outputs").is_length(2)
    returned_ids = {str(r["id"]) for r in result}
    assert_that(returned_ids).described_as("correct ids returned").is_equal_to({str(a["id"]), str(c["id"])})
    returned_templates = {r["path_template"] for r in result}
    assert_that(returned_templates).described_as("correct templates").is_equal_to({"/a.json", "/c.json"})
    # b was not requested and should not be present
    assert_that(str(b["id"])).described_as("unrequested output absent").is_not_in(returned_ids)


async def test_get_by_ids_empty_list(pool):
    """get_by_ids returns an empty list when given no IDs."""
    outputs = Outputs(pool)
    result = await outputs.get_by_ids(ids=[])
    assert_that(result).described_as("empty list for empty ids").is_equal_to([])


async def test_get_by_ids_unknown_ids(pool):
    """get_by_ids returns an empty list when no IDs match."""
    outputs = Outputs(pool)
    result = await outputs.get_by_ids(ids=["00000000-0000-0000-0000-ffffffffffff"])
    assert_that(result).described_as("empty list for unknown ids").is_equal_to([])


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
    assert_that(templates).described_as("both shown with include_archived").contains("/keep.json", "/archive.json")


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
    created = await outputs.create(path_template="/z.json", format="json", dimension_ids=[dim_id])

    dims = await outputs.get_dimensions(output_id=str(created["id"]))
    assert_that(dims).described_as("one dimension").is_length(1)
    assert_that(str(dims[0]["id"])).is_equal_to(dim_id)
