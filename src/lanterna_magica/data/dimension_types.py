from asyncpg import Pool

from lanterna_magica.errors import NotFoundError, ValidationError

from .utils import queries, validate_name


class DimensionTypes:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_dimension_types(
        self, *, include_archived: bool = False
    ) -> list[dict]:
        rows = [
            dict(r)
            async for r in queries.get_dimension_types(
                self.pool, include_archived=include_archived
            )
        ]
        return rows

    async def get_dimension_types_by_ids(self, ids: list[str]) -> list[dict]:
        rows = [
            dict(r)
            async for r in queries.get_dimension_types_by_ids(self.pool, ids=ids)
        ]
        return rows

    async def create_dimension_type(self, *, name: str, priority: int) -> dict:
        validate_name(name)
        row = await queries.create_dimension_type(
            self.pool, name=name, priority=priority
        )
        return dict(row)

    async def archive_dimension_type(self, id: str) -> dict:
        row = await queries.archive_dimension_type(self.pool, id=id)
        if not row:
            raise NotFoundError("Dimension type not found or already archived")
        return dict(row)

    async def unarchive_dimension_type(self, id: str) -> dict:
        row = await queries.unarchive_dimension_type(self.pool, id=id)
        if not row:
            raise NotFoundError("Dimension type not found or not archived")
        return dict(row)
