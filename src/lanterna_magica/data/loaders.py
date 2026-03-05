from aiodataloader import DataLoader
from asyncpg import Pool

import json

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


class ConfigurationLoader(DataLoader):
    def __init__(self, pool: Pool):
        super().__init__()
        self.pool = pool

    async def batch_load_fn(self, ids):
        rows = []
        async for r in queries.get_configurations_by_ids(self.pool, ids=list(ids)):
            d = dict(r)
            if isinstance(d.get("body"), str):
                d["body"] = json.loads(d["body"])
            rows.append(d)
        by_id = {str(r["id"]): r for r in rows}
        return [by_id.get(str(i)) for i in ids]


def create_loaders(pool: Pool) -> dict:
    return {
        "configuration_loader": ConfigurationLoader(pool),
        "service_loader": ServiceLoader(pool),
        "environment_loader": EnvironmentLoader(pool),
        "shared_value_loader": SharedValueLoader(pool),
    }
