import json
import logging
from pathlib import Path

import asyncpg
from yoyo import get_backend, read_migrations

from lanterna_magica.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


def _get_migrations_dir() -> Path:
    configured = settings.get("migrations_dir")
    return Path(configured) if configured else _DEFAULT_MIGRATIONS_DIR


def get_dsn() -> str:
    db = settings.db
    return f"postgresql://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}"


def apply_migrations() -> None:
    dsn = get_dsn()
    backend = get_backend(dsn)
    migrations = read_migrations(str(_get_migrations_dir()))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))
    logger.info("Migrations applied")


async def _init_connection(conn: asyncpg.Connection):
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def create_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(get_dsn(), init=_init_connection)
