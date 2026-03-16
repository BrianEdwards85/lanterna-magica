from collections import defaultdict

from asyncpg import Pool

from lanterna_magica.errors import NotFoundError, ValidationError

from .utils import (
    build_connection,
    compute_scope_hash,
    decode_cursor,
    page_limit,
    queries,
    require_row,
)


class Configurations:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_configurations(
        self,
        *,
        dimension_ids: list[str] | None = None,
        include_base: bool = True,
        current_only: bool = False,
        first: int | None = None,
        after: str | None = None,
    ) -> dict:
        limit = page_limit(first)
        after_id = decode_cursor(after) if after else None

        rows = [
            dict(r)
            async for r in queries.get_configurations(
                self.pool,
                dimension_ids=dimension_ids,
                include_base=include_base,
                current_only=current_only,
                after_id=after_id,
                page_limit=limit + 1,
            )
        ]
        return build_connection(rows, "id", limit)

    async def get_configurations_by_ids(self, ids: list[str]) -> list[dict]:
        rows = [
            dict(r) async for r in queries.get_configurations_by_ids(self.pool, ids=ids)
        ]
        return rows


    async def get_configurations_by_shared_value(
        self,
        *,
        shared_value_id: str,
        include_archived: bool = False,
        first: int | None = None,
        after: str | None = None,
    ) -> dict:
        limit = page_limit(first)
        after_id = decode_cursor(after) if after else None
        rows = [
            dict(r)
            async for r in queries.get_configurations_by_shared_value_id(
                self.pool,
                shared_value_id=shared_value_id,
                include_archived=include_archived,
                after_id=after_id,
                page_limit=limit + 1,
            )
        ]
        return build_connection(rows, "id", limit)

    async def create_configuration(
        self,
        *,
        dimension_ids: list[str],
        body: dict | list,
        substitutions: list[dict] | None = None,
    ) -> dict:
        effective_ids = list(dimension_ids)
        missing = [
            dict(r)
            async for r in queries.get_missing_base_dimensions(
                self.pool, dimension_ids=effective_ids,
            )
        ]
        effective_ids.extend(str(d["id"]) for d in missing)

        dims = [
            dict(r)
            async for r in queries.get_dimensions_by_ids(self.pool, ids=effective_ids)
        ]
        type_ids = [str(d["type_id"]) for d in dims]
        if len(type_ids) != len(set(type_ids)):
            raise ValidationError("Scope contains multiple dimensions of the same type")

        scope_hash = compute_scope_hash(effective_ids)

        async with self.pool.acquire() as conn, conn.transaction():
            await queries.unset_current_configuration(conn, scope_hash=scope_hash)
            row = await queries.create_configuration(
                conn, scope_hash=scope_hash, body=body
            )
            config = dict(row)

            for dim_id in effective_ids:
                await queries.insert_configuration_scope(
                    conn,
                    configuration_id=str(config["id"]),
                    dimension_id=dim_id,
                )

            created_subs = []
            if substitutions:
                for sub in substitutions:
                    sub_row = await queries.create_config_substitution(
                        conn,
                        configuration_id=str(config["id"]),
                        jsonpath=sub["jsonpath"],
                        shared_value_id=sub["shared_value_id"],
                    )
                    created_subs.append(dict(sub_row))

            config["substitutions"] = created_subs

        return config

    async def set_configuration_current(self, *, id: str, is_current: bool) -> dict:
        if is_current:
            rows = [
                dict(r)
                async for r in queries.get_configurations_by_ids(self.pool, ids=[id])
            ]
            if not rows:
                raise NotFoundError("Configuration not found")
            config = rows[0]
            async with self.pool.acquire() as conn, conn.transaction():
                await queries.unset_current_configuration(
                    conn, scope_hash=str(config["scope_hash"]),
                )
                row = await queries.set_configuration_current(conn, id=id)
                if not row:
                    raise NotFoundError("Configuration not found or already current")
                return dict(row)
        else:
            return await require_row(
                queries.unset_single_configuration_current,
                "Configuration not found or already not current",
                self.pool,
                id=id,
            )

    async def update_config_substitution(
        self,
        *,
        configuration_id: str,
        jsonpath: str,
        shared_value_id: str,
    ) -> dict:
        row = await queries.update_config_substitution(
            self.pool,
            configuration_id=configuration_id,
            jsonpath=jsonpath,
            shared_value_id=shared_value_id,
        )
        if not row:
            raise NotFoundError("Config substitution not found")
        return dict(row)

    async def get_configurations_by_scope(
        self,
        *,
        scope_hash: str,
        first: int | None = None,
        after: str | None = None,
    ) -> dict:
        limit = page_limit(first)
        after_id = decode_cursor(after) if after else None
        rows = [
            dict(r)
            async for r in queries.get_configurations_by_scope_hash(
                self.pool,
                scope_hash=scope_hash,
                after_id=after_id,
                page_limit=limit + 1,
            )
        ]
        return build_connection(rows, "id", limit)

    async def get_substitutions(self, *, configuration_id: str) -> list[dict]:
        rows = [
            dict(r)
            async for r in queries.get_substitutions_for_config(
                self.pool, configuration_id=configuration_id
            )
        ]
        return rows

    async def get_for_rest_scope(self, *, dimension_ids: list[str]) -> list[dict]:
        configs = [
            dict(r)
            async for r in queries.get_configs_for_rest_scope(
                self.pool, dimension_ids=dimension_ids
            )
        ]
        ids = [str(c["id"]) for c in configs]
        by_config: defaultdict[str, list] = defaultdict(list)
        async for r in queries.get_substitutions_by_config_ids(self.pool, ids=ids):
            d = dict(r)
            by_config[str(d["configuration_id"])].append(d)
        for config in configs:
            config["substitutions"] = by_config[str(config["id"])]
        return configs
