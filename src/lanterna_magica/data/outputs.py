from __future__ import annotations

from asyncpg import Pool

from lanterna_magica.errors import NotFoundError

from .utils import build_connection, decode_cursor, page_limit, queries


class Outputs:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def create(
        self,
        *,
        path_template: str,
        format: str,
        dimension_ids: list[str],
    ) -> dict:
        async with self.pool.acquire() as conn, conn.transaction():
            row = await queries.create_output(
                conn, path_template=path_template, format=format
            )
            output = dict(row)

            for dim_id in dimension_ids:
                await queries.insert_output_dimension(
                    conn,
                    output_id=str(output["id"]),
                    dimension_id=dim_id,
                )

            dims = [
                dict(r)
                async for r in queries.get_dimensions_for_output(
                    conn, output_id=str(output["id"])
                )
            ]
            output["dimensions"] = dims

        return output

    async def get(self, *, id: str) -> dict | None:
        row = await queries.get_output(self.pool, id=id)
        if row is None:
            return None
        return dict(row)

    async def list(
        self,
        *,
        include_archived: bool = False,
        first: int | None = None,
        after: str | None = None,
    ) -> dict:
        limit = page_limit(first)
        after_id = decode_cursor(after) if after else None

        rows = [
            dict(r)
            async for r in queries.get_outputs(
                self.pool,
                include_archived=include_archived,
                after_id=after_id,
                page_limit=limit + 1,
            )
        ]
        return build_connection(rows, "id", limit)

    async def archive(self, *, id: str) -> dict:
        row = await queries.archive_output(self.pool, id=id)
        if not row:
            raise NotFoundError("Output not found or already archived")
        return dict(row)

    async def get_dimensions(self, *, output_id: str) -> list[dict]:
        rows = [
            dict(r)
            async for r in queries.get_dimensions_for_output(
                self.pool, output_id=output_id
            )
        ]
        return rows

    async def upsert_result(
        self,
        *,
        output_id: str,
        scope_hash: str,
        path: str,
        content: str,
        succeeded: bool,
        error: str | None = None,
        written_by: str = "00000000-0000-0000-0000-000000000000",
    ) -> dict:
        row = await queries.upsert_output_result(
            self.pool,
            output_id=output_id,
            scope_hash=scope_hash,
            path=path,
            content=content,
            succeeded=succeeded,
            error=error,
            written_by=written_by,
        )
        return dict(row)

    async def get_results(self, *, output_id: str) -> list[dict]:
        rows = [
            dict(r)
            async for r in queries.get_results_for_output(
                self.pool, output_id=output_id
            )
        ]
        return rows
