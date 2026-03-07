from asyncpg import Pool

from lanterna_magica.errors import ValidationError

from .utils import build_connection, decode_cursor, page_limit, queries, require_row, sanitize_search, validate_name


class Dimensions:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_dimensions(
        self,
        *,
        type_id: str,
        search: str | None = None,
        include_base: bool = True,
        include_archived: bool = False,
        first: int | None = None,
        after: str | None = None,
    ) -> dict:
        limit = page_limit(first)
        search = sanitize_search(search) if search else None
        after_id = decode_cursor(after, search=search) if after else None

        rows = [
            dict(r)
            async for r in queries.get_dimensions(
                self.pool,
                type_id=type_id,
                include_base=include_base,
                include_archived=include_archived,
                search=search,
                after_id=after_id,
                page_limit=limit + 1,
            )
        ]
        return build_connection(rows, "id", limit, search=search)

    async def get_dimensions_by_ids(self, ids: list[str]) -> list[dict]:
        rows = [
            dict(r)
            async for r in queries.get_dimensions_by_ids(self.pool, ids=ids)
        ]
        return rows

    async def get_base_dimension(self, type_id: str) -> dict:
        return await require_row(
            queries.get_base_dimension, "Base dimension not found for this type",
            self.pool, type_id=type_id,
        )

    async def create_dimension(
        self, *, type_id: str, name: str, description: str | None = None
    ) -> dict:
        validate_name(name)
        row = await queries.create_dimension(
            self.pool, type_id=type_id, name=name, description=description
        )
        return dict(row)

    async def update_dimension(
        self, *, id: str, name: str | None = None, description: str | None = None
    ) -> dict:
        if name is None and description is None:
            raise ValidationError("At least one field must be provided")
        if name is not None:
            validate_name(name)
        return await require_row(
            queries.update_dimension, "Dimension not found",
            self.pool, id=id, name=name, description=description,
        )

    async def archive_dimension(self, id: str) -> dict:
        return await require_row(
            queries.archive_dimension, "Dimension not found or already archived",
            self.pool, id=id,
        )

    async def unarchive_dimension(self, id: str) -> dict:
        return await require_row(
            queries.unarchive_dimension, "Dimension not found or not archived",
            self.pool, id=id,
        )
