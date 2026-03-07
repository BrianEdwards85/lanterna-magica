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


class DimensionTypeLoader(_ByIdLoader):
    query_fn = queries.get_dimension_types_by_ids


class DimensionLoader(_ByIdLoader):
    query_fn = queries.get_dimensions_by_ids


class SharedValueLoader(_ByIdLoader):
    query_fn = queries.get_shared_values_by_ids


class ConfigurationLoader(_ByIdLoader):
    query_fn = queries.get_configurations_by_ids


class _ScopesByParentLoader(DataLoader):
    """One-to-many loader: parent_id -> list of dimension rows."""

    query_fn = None
    parent_key = None

    def __init__(self, pool: Pool):
        super().__init__()
        self.pool = pool

    async def batch_load_fn(self, parent_ids):
        by_parent = defaultdict(list)
        async for r in self.query_fn(self.pool, ids=list(parent_ids)):
            d = dict(r)
            by_parent[str(d[self.parent_key])].append(d)
        return [by_parent.get(str(pid), []) for pid in parent_ids]


class ScopesByConfigLoader(_ScopesByParentLoader):
    query_fn = queries.get_scopes_by_config_ids
    parent_key = "configuration_id"


class ScopesByRevisionLoader(_ScopesByParentLoader):
    query_fn = queries.get_scopes_by_revision_ids
    parent_key = "revision_id"


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
        "dimension_type_loader": DimensionTypeLoader(pool),
        "dimension_loader": DimensionLoader(pool),
        "shared_value_loader": SharedValueLoader(pool),
        "substitution_loader": SubstitutionsByConfigLoader(pool),
        "config_scopes_loader": ScopesByConfigLoader(pool),
        "revision_scopes_loader": ScopesByRevisionLoader(pool),
    }
