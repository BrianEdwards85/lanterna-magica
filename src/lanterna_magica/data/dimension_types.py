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

    async def create_dimension_type(self, *, name: str) -> dict:
        validate_name(name)
        row = await queries.create_dimension_type(
            self.pool, name=name
        )
        dt = dict(row)
        await queries.create_base_dimension(
            self.pool, type_id=str(dt["id"]), name="global",
            description=f"Default base for {name} dimension",
        )
        return dt

    async def update_dimension_type(
        self, *, id: str, name: str
    ) -> dict:
        validate_name(name)
        row = await queries.update_dimension_type(
            self.pool, id=id, name=name
        )
        if not row:
            raise NotFoundError("Dimension type not found or archived")
        return dict(row)

    async def swap_dimension_type_priorities(
        self, *, id_a: str, id_b: str
    ) -> list[dict]:
        if id_a == id_b:
            raise ValidationError("Cannot swap a dimension type with itself")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row_a = await queries.get_dimension_type_priority(conn, id=id_a)
                row_b = await queries.get_dimension_type_priority(conn, id=id_b)
                if not row_a or not row_b:
                    raise NotFoundError("One or both dimension types not found")
                pri_a, pri_b = row_a["priority"], row_b["priority"]
                # Three-step swap to avoid unique constraint violation
                await queries.set_dimension_type_priority(conn, id=id_a, priority=-1)
                await queries.set_dimension_type_priority(conn, id=id_b, priority=pri_a)
                await queries.set_dimension_type_priority(conn, id=id_a, priority=pri_b)
        rows = [
            dict(r)
            async for r in queries.get_dimension_types_by_ids(
                self.pool, ids=[id_a, id_b]
            )
        ]
        return rows

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
