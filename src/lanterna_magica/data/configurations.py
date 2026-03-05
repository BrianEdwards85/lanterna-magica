from asyncpg import Pool

from lanterna_magica.errors import NotFoundError

from .utils import build_connection, decode_cursor, page_limit, queries


def _parse_row(row):
    return dict(row)


class Configurations:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_configurations(
        self,
        *,
        service_id: str | None = None,
        environment_id: str | None = None,
        include_global: bool = True,
        first: int | None = None,
        after: str | None = None,
    ) -> dict:
        limit = page_limit(first)
        after_id = decode_cursor(after) if after else None

        rows = [
            _parse_row(r)
            async for r in queries.get_configurations(
                self.pool,
                service_id=service_id,
                environment_id=environment_id,
                include_global=include_global,
                after_id=after_id,
                page_limit=limit + 1,
            )
        ]
        return build_connection(rows, "id", limit)

    async def create_configuration(
        self,
        *,
        service_id: str,
        environment_id: str,
        body: dict | list,
        substitutions: list[dict] | None = None,
    ) -> dict:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await queries.unset_current_configuration(
                    conn,
                    service_id=service_id,
                    environment_id=environment_id,
                )
                row = await queries.create_configuration(
                    conn,
                    service_id=service_id,
                    environment_id=environment_id,
                    body=body,
                )
                config = _parse_row(row)

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

    async def get_substitutions(self, *, configuration_id: str) -> list[dict]:
        rows = [
            dict(r)
            async for r in queries.get_substitutions_for_config(
                self.pool, configuration_id=configuration_id
            )
        ]
        return rows
