from asyncpg import Pool

from lanterna_magica.errors import ValidationError

from .utils import (
    build_connection,
    compute_scope_hash,
    decode_cursor,
    page_limit,
    queries,
    require_row,
    validate_name,
)


class SharedValues:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_shared_values(
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
            async for r in queries.get_shared_values(
                self.pool,
                include_archived=include_archived,
                after_id=after_id,
                page_limit=limit + 1,
            )
        ]
        return build_connection(rows, "id", limit)

    async def search_shared_values(
        self,
        *,
        search: str,
        include_archived: bool = False,
        limit: int | None = None,
    ) -> list[dict]:
        effective_limit = page_limit(limit)
        return [
            dict(r)
            async for r in queries.search_shared_values(
                self.pool,
                query=search,
                include_archived=include_archived,
                page_limit=effective_limit,
            )
        ]

    async def get_shared_values_by_ids(self, ids: list[str]) -> list[dict]:
        rows = [
            dict(r) async for r in queries.get_shared_values_by_ids(self.pool, ids=ids)
        ]
        return rows

    async def create_shared_value(self, *, name: str) -> dict:
        validate_name(name)
        row = await queries.create_shared_value(self.pool, name=name)
        return dict(row)

    async def update_shared_value(self, *, id: str, name: str | None = None) -> dict:
        if name is None:
            raise ValidationError("At least one field must be provided")
        validate_name(name)
        return await require_row(
            queries.update_shared_value,
            "Shared value not found or is archived",
            self.pool,
            id=id,
            name=name,
        )

    async def archive_shared_value(self, id: str) -> dict:
        return await require_row(
            queries.archive_shared_value,
            "Shared value not found or already archived",
            self.pool,
            id=id,
        )

    async def unarchive_shared_value(self, id: str) -> dict:
        return await require_row(
            queries.unarchive_shared_value,
            "Shared value not found or not archived",
            self.pool,
            id=id,
        )

    async def get_revisions(
        self,
        *,
        shared_value_id: str,
        dimension_ids: list[str] | None = None,
        include_base: bool = True,
        current_only: bool = False,
        first: int | None = None,
        after: str | None = None,
    ) -> dict:
        limit = page_limit(first)
        after_id = decode_cursor(after) if after else None

        rows = [
            dict(r)
            async for r in queries.get_revisions(
                self.pool,
                shared_value_id=shared_value_id,
                dimension_ids=dimension_ids,
                include_base=include_base,
                current_only=current_only,
                after_id=after_id,
                page_limit=limit + 1,
            )
        ]
        return build_connection(rows, "id", limit)

    async def create_revision(
        self,
        *,
        shared_value_id: str,
        dimension_ids: list[str],
        value: dict | list | str | int | float | bool | None,
    ) -> dict:
        effective_ids = list(dimension_ids)
        missing = [
            dict(r)
            async for r in queries.get_missing_base_dimensions(
                self.pool, dimension_ids=effective_ids,
            )
        ]
        effective_ids.extend(str(d["id"]) for d in missing)

        scope_hash = compute_scope_hash(effective_ids)

        async with self.pool.acquire() as conn, conn.transaction():
            await queries.unset_current_revision(
                conn,
                shared_value_id=shared_value_id,
                scope_hash=scope_hash,
            )
            row = await queries.create_revision(
                conn,
                shared_value_id=shared_value_id,
                scope_hash=scope_hash,
                value=value,
            )
            revision = dict(row)

            for dim_id in effective_ids:
                await queries.insert_revision_scope(
                    conn,
                    revision_id=str(revision["id"]),
                    dimension_id=dim_id,
                )

        return revision
