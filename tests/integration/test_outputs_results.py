from assertpy import assert_that
from gql import _create_env_dim, _create_service_dim

from lanterna_magica.data.loaders import OutputDimensionsLoader, OutputResultsLoader
from lanterna_magica.data.outputs import Outputs

# -- Tests --


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
    assert_that(paths).described_as("ordered by path asc").is_equal_to(["/a/r.json", "/b/r.json"])


async def test_output_dimensions_loader_batches_multiple_outputs(pool):
    """OutputDimensionsLoader loads dimensions for multiple outputs in one batch."""
    svc_id = await _create_service_dim(pool)
    env_id = await _create_env_dim(pool)
    outputs = Outputs(pool)

    out_a = await outputs.create(path_template="/a.json", format="json", dimension_ids=[svc_id])
    out_b = await outputs.create(path_template="/b.json", format="json", dimension_ids=[env_id])
    out_c = await outputs.create(path_template="/c.json", format="json", dimension_ids=[])

    loader = OutputDimensionsLoader(pool)
    id_a = str(out_a["id"])
    id_b = str(out_b["id"])
    id_c = str(out_c["id"])

    dims_a, dims_b, dims_c = await loader.load_many([id_a, id_b, id_c])

    assert_that(dims_a).described_as("output_a has one dimension").is_length(1)
    assert_that(str(dims_a[0]["id"])).described_as("output_a dimension matches svc_id").is_equal_to(svc_id)

    assert_that(dims_b).described_as("output_b has one dimension").is_length(1)
    assert_that(str(dims_b[0]["id"])).described_as("output_b dimension matches env_id").is_equal_to(env_id)

    assert_that(dims_c).described_as("output_c has no dimensions").is_length(0)


async def test_output_results_loader_batches_multiple_outputs(pool):
    """OutputResultsLoader loads results for multiple outputs in one batch."""
    outputs = Outputs(pool)

    out_a = await outputs.create(path_template="/a.json", format="json", dimension_ids=[])
    out_b = await outputs.create(path_template="/b.json", format="json", dimension_ids=[])
    out_c = await outputs.create(path_template="/c.json", format="json", dimension_ids=[])

    await outputs.upsert_result(
        output_id=str(out_a["id"]),
        scope_hash="00000000-0000-0000-0000-000000000020",
        path="/a/1.json",
        content="{}",
        succeeded=True,
    )
    await outputs.upsert_result(
        output_id=str(out_a["id"]),
        scope_hash="00000000-0000-0000-0000-000000000021",
        path="/a/2.json",
        content="{}",
        succeeded=True,
    )
    await outputs.upsert_result(
        output_id=str(out_b["id"]),
        scope_hash="00000000-0000-0000-0000-000000000022",
        path="/b/1.json",
        content="{}",
        succeeded=False,
        error="oops",
    )

    loader = OutputResultsLoader(pool)
    id_a = str(out_a["id"])
    id_b = str(out_b["id"])
    id_c = str(out_c["id"])

    results_a, results_b, results_c = await loader.load_many([id_a, id_b, id_c])

    assert_that(results_a).described_as("output_a has two results").is_length(2)
    paths_a = [r["path"] for r in results_a]
    assert_that(paths_a).described_as("output_a results ordered by path").is_equal_to(["/a/1.json", "/a/2.json"])

    assert_that(results_b).described_as("output_b has one result").is_length(1)
    assert_that(results_b[0]["error"]).described_as("output_b result has error").is_equal_to("oops")

    assert_that(results_c).described_as("output_c has no results").is_length(0)
