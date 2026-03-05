from asyncpg import Pool

from lanterna_magica.errors import NotFoundError, ValidationError

from .utils import build_connection, decode_cursor, page_limit, queries, validate_name


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
            dict(r)
            async for r in queries.get_shared_values_by_ids(self.pool, ids=ids)
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
        row = await queries.update_shared_value(self.pool, id=id, name=name)
        if not row:
            raise NotFoundError("Shared value not found or is archived")
        return dict(row)

    async def archive_shared_value(self, id: str) -> dict:
        row = await queries.archive_shared_value(self.pool, id=id)
        if not row:
            raise NotFoundError("Shared value not found or already archived")
        return dict(row)

    async def unarchive_shared_value(self, id: str) -> dict:
        row = await queries.unarchive_shared_value(self.pool, id=id)
        if not row:
            raise NotFoundError("Shared value not found or not archived")
        return dict(row)

    async def get_revisions(
        self,
        *,
        shared_value_id: str,
        service_id: str | None = None,
        environment_id: str | None = None,
        include_global: bool = True,
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
                service_id=service_id,
                environment_id=environment_id,
                include_global=include_global,
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
        service_id: str,
        environment_id: str,
        value: dict | list | str | int | float | bool | None,
    ) -> dict:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await queries.unset_current_revision(
                    conn,
                    shared_value_id=shared_value_id,
                    service_id=service_id,
                    environment_id=environment_id,
                )
                row = await queries.create_revision(
                    conn,
                    shared_value_id=shared_value_id,
                    service_id=service_id,
                    environment_id=environment_id,
                    value=value,
                )
        return dict(row)
