import json
from collections import defaultdict

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


class SubstitutionsByConfigLoader(DataLoader):
    """One-to-many loader: configuration_id -> list of substitution rows."""

    def __init__(self, pool: Pool):
        super().__init__()
        self.pool = pool

    async def batch_load_fn(self, config_ids):
        by_config = defaultdict(list)
        async for r in queries.get_substitutions_by_config_ids(
            self.pool, ids=list(config_ids)
        ):
            d = dict(r)
            by_config[str(d["configuration_id"])].append(d)
        return [by_config.get(str(cid), []) for cid in config_ids]


def create_loaders(pool: Pool) -> dict:
    return {
        "configuration_loader": ConfigurationLoader(pool),
        "service_loader": ServiceLoader(pool),
        "environment_loader": EnvironmentLoader(pool),
        "shared_value_loader": SharedValueLoader(pool),
        "substitution_loader": SubstitutionsByConfigLoader(pool),
    }
