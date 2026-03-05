from asyncpg import Pool

from .utils import build_connection, decode_cursor, page_limit, queries, sanitize_search, validate_name


class Services:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_services(
        self,
        *,
        search: str | None = None,
        include_archived: bool = False,
        first: int | None = None,
        after: str | None = None,
    ) -> dict:
        limit = page_limit(first)
        after_id = decode_cursor(after, search=search) if after else None
        search = sanitize_search(search) if search else None

        rows = [
            dict(r)
            async for r in queries.get_services(
                self.pool,
                include_archived=include_archived,
                search=search,
                after_id=after_id,
                page_limit=limit + 1,
            )
        ]
        return build_connection(rows, "id", limit, search=search)

    async def get_services_by_ids(self, ids: list[str]) -> list[dict]:
        rows = [
            dict(r)
            async for r in queries.get_services_by_ids(self.pool, ids=ids)
        ]
        return rows

    async def create_service(self, *, name: str, description: str | None = None) -> dict:
        validate_name(name)
        row = await queries.create_service(self.pool, name=name, description=description)
        return dict(row)

    async def update_service(
        self, *, id: str, name: str | None = None, description: str | None = None
    ) -> dict:
        if name is not None:
            validate_name(name)
        row = await queries.update_service(
            self.pool, id=id, name=name, description=description
        )
        if not row:
            raise ValueError("Service not found")
        return dict(row)

    async def archive_service(self, id: str) -> dict:
        row = await queries.archive_service(self.pool, id=id)
        if not row:
            raise ValueError("Service not found or already archived")
        return dict(row)

    async def unarchive_service(self, id: str) -> dict:
        row = await queries.unarchive_service(self.pool, id=id)
        if not row:
            raise ValueError("Service not found or not archived")
        return dict(row)
