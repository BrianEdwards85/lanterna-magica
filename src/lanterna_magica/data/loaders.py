import json

from aiodataloader import DataLoader
from asyncpg import Pool

from .utils import queries


class _ByIdLoader(DataLoader):
    query_fn = None

    def __init__(self, pool: Pool):
        super().__init__()
        self.pool = pool

    async def batch_load_fn(self, ids):
        rows = [dict(r) async for r in self.query_fn(self.pool, ids=list(ids))]
        by_id = {str(r["id"]): r for r in rows}
        return [by_id.get(str(i)) for i in ids]


class ServiceLoader(_ByIdLoader):
    query_fn = queries.get_services_by_ids


class EnvironmentLoader(_ByIdLoader):
    query_fn = queries.get_environments_by_ids


class SharedValueLoader(_ByIdLoader):
    query_fn = queries.get_shared_values_by_ids


class ConfigurationLoader(_ByIdLoader):
    query_fn = queries.get_configurations_by_ids

    async def batch_load_fn(self, ids):
        rows = []
        async for r in self.query_fn(self.pool, ids=list(ids)):
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
