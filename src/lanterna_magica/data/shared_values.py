from asyncpg import Connection, Pool

from lanterna_magica.errors import NotFoundError, ValidationError

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
        search: str | None = None,
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
                search=search,
                after_id=after_id,
                page_limit=limit + 1,
            )
        ]
        return build_connection(rows, "id", limit)

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

    async def resolve_for_scope(
        self,
        *,
        shared_value_id: str,
        dimension_ids: list[str],
        conn: Connection | Pool | None = None,
    ) -> dict | None:
        conn_or_pool = conn if conn is not None else self.pool
        row = await queries.resolve_shared_value_for_scope(
            conn_or_pool,
            shared_value_id=shared_value_id,
            dimension_ids=dimension_ids,
        )
        return dict(row) if row else None

    async def set_revision_current(self, *, id: str, is_current: bool) -> dict:
        if is_current:
            rows = [
                dict(r)
                async for r in queries.get_revision_by_ids(self.pool, ids=[id])
            ]
            if not rows:
                raise NotFoundError("Revision not found")
            rev = rows[0]
            async with self.pool.acquire() as conn, conn.transaction():
                await queries.unset_current_revision(
                    conn,
                    shared_value_id=str(rev["shared_value_id"]),
                    scope_hash=str(rev["scope_hash"]),
                )
                row = await queries.set_revision_current(conn, id=id)
                if not row:
                    raise NotFoundError("Revision not found or already current")
                return dict(row)
        else:
            return await require_row(
                queries.unset_single_revision_current,
                "Revision not found or already not current",
                self.pool,
                id=id,
            )
