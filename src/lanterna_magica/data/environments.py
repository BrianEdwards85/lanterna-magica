from asyncpg import Pool

from .utils import build_connection, decode_cursor, page_limit, queries, sanitize_search, validate_name


class Environments:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_environments(
        self,
        *,
        search: str | None = None,
        include_archived: bool = False,
        first: int | None = None,
        after: str | None = None,
    ) -> dict:
        limit = page_limit(first)
        search = sanitize_search(search) if search else None
        after_id = decode_cursor(after, search=search) if after else None

        rows = [
            dict(r)
            async for r in queries.get_environments(
                self.pool,
                include_archived=include_archived,
                search=search,
                after_id=after_id,
                page_limit=limit + 1,
            )
        ]
        return build_connection(rows, "id", limit, search=search)

    async def get_environments_by_ids(self, ids: list[str]) -> list[dict]:
        rows = [
            dict(r)
            async for r in queries.get_environments_by_ids(self.pool, ids=ids)
        ]
        return rows

    async def create_environment(self, *, name: str, description: str | None = None) -> dict:
        validate_name(name)
        row = await queries.create_environment(self.pool, name=name, description=description)
        return dict(row)

    async def update_environment(
        self, *, id: str, name: str | None = None, description: str | None = None
    ) -> dict:
        if name is None and description is None:
            raise ValueError("At least one field must be provided")
        if name is not None:
            validate_name(name)
        row = await queries.update_environment(
            self.pool, id=id, name=name, description=description
        )
        if not row:
            raise ValueError("Environment not found")
        return dict(row)

    async def archive_environment(self, id: str) -> dict:
        row = await queries.archive_environment(self.pool, id=id)
        if not row:
            raise ValueError("Environment not found or already archived")
        return dict(row)

    async def unarchive_environment(self, id: str) -> dict:
        row = await queries.unarchive_environment(self.pool, id=id)
        if not row:
            raise ValueError("Environment not found or not archived")
        return dict(row)
