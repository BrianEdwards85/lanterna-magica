from collections import defaultdict

from aiodataloader import DataLoader
from asyncpg import Pool

from .utils import queries


class ServiceLoader(DataLoader):
    def __init__(self, pool: Pool):
        super().__init__()
        self.pool = pool

    async def batch_load_fn(self, ids):
        rows = [
            dict(r)
            async for r in queries.get_services_by_ids(self.pool, ids=list(ids))
        ]
        by_id = {str(r["id"]): r for r in rows}
        return [by_id.get(str(i)) for i in ids]


class EnvironmentLoader(DataLoader):
    def __init__(self, pool: Pool):
        super().__init__()
        self.pool = pool

    async def batch_load_fn(self, ids):
        rows = [
            dict(r)
            async for r in queries.get_environments_by_ids(self.pool, ids=list(ids))
        ]
        by_id = {str(r["id"]): r for r in rows}
        return [by_id.get(str(i)) for i in ids]


class SharedValueLoader(DataLoader):
    def __init__(self, pool: Pool):
        super().__init__()
        self.pool = pool

    async def batch_load_fn(self, ids):
        rows = [
            dict(r)
            async for r in queries.get_shared_values_by_ids(self.pool, ids=list(ids))
        ]
        by_id = {str(r["id"]): r for r in rows}
        return [by_id.get(str(i)) for i in ids]


class SharedValueRevisionLoader(DataLoader):
    """Batches current revisions by shared_value_id. Returns a list per id."""

    def __init__(self, pool: Pool):
        super().__init__()
        self.pool = pool

    async def batch_load_fn(self, shared_value_ids):
        rows = [
            dict(r)
            async for r in queries.get_current_revisions_by_shared_value_ids(
                self.pool, shared_value_ids=list(shared_value_ids)
            )
        ]
        by_sv_id = defaultdict(list)
        for r in rows:
            by_sv_id[str(r["shared_value_id"])].append(r)
        return [by_sv_id.get(str(i), []) for i in shared_value_ids]


def create_loaders(pool: Pool) -> dict:
    return {
        "service_loader": ServiceLoader(pool),
        "environment_loader": EnvironmentLoader(pool),
        "shared_value_loader": SharedValueLoader(pool),
        "shared_value_revision_loader": SharedValueRevisionLoader(pool),
    }
