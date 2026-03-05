# Design Reference

This document describes the architecture, coding conventions, and patterns used in lanterna-magica. Follow these when making changes or adding features.

## Architecture

### Layering

```
GraphQL Request
    │
    ▼
Resolvers (resolvers/*.py)        ← GraphQL field resolution, input unpacking
    │
    ▼
Data Layer (data/*.py)            ← Business logic, pagination, transactions
    │
    ▼
aiosql Queries (sql/*.sql)        ← Named SQL queries with parameter binding
    │
    ▼
asyncpg Pool → PostgreSQL
```

- **Resolvers** handle GraphQL field resolution and input unpacking. They delegate all business logic to the data layer.
- **Data classes** wrap aiosql queries, manage transactions, and return plain dicts.
- **SQL files** define all database queries via aiosql named-query syntax.
- **DataLoaders** batch entity lookups to prevent N+1 queries on nested GraphQL fields.

### Dependency Injection

Dependencies are wired in `resolvers/__init__.py` → `create_gql()`:

```python
def create_gql(pool) -> GraphQL:
    configurations = Configurations(pool)
    environments = Environments(pool)
    services = Services(pool)
    shared_values = SharedValues(pool)

    schema = make_executable_schema(
        type_defs,
        *get_configuration_resolvers(configurations),
        *get_environment_resolvers(environments),
        *get_service_resolvers(services),
        *get_shared_value_resolvers(shared_values),
        datetime_scalar, json_scalar,
        convert_names_case=True,
    )
    return GraphQL(schema, context_value=lambda request, _data=None: {
        "pool": pool,
        **create_loaders(pool),
    })
```

Data classes take `pool`. No global singletons. Fresh DataLoaders are created per request.

### Request Lifecycle

```
HTTP POST /graphql
  │
  ▼
FastAPI → graphql_endpoint → app.state.graphql (Ariadne GraphQL ASGI app)
  │
  ├─ context_value callback
  │    ├─ Injects pool into context
  │    └─ Creates fresh DataLoaders for this request
  │
  └─ Resolver executes
       ├─ Delegates to data layer class
       │    └─ Data class runs aiosql queries against the pool
       └─ Nested fields use DataLoaders to batch lookups
```

### Startup (Lifespan)

```python
@asynccontextmanager
async def lifespan(app):
    apply_migrations()           # yoyo runs pending SQL migrations synchronously
    pool = await create_pool()   # asyncpg pool with JSONB codec
    app.state.pool = pool
    app.state.graphql = create_gql(pool)
    yield
    await pool.close()
```

---

## Directory Structure

```
src/lanterna_magica/
├── __init__.py
├── app.py                   # FastAPI app, lifespan, health check, GraphQL endpoint
├── config.py                # Dynaconf settings object
├── db.py                    # Pool creation, DSN builder, migration runner
├── schema/                  # .graphql files (schema-first)
│   ├── schema.graphql       # Root Query, Mutation, PageInfo
│   ├── scalars.graphql      # DateTime, JSON scalar definitions
│   ├── service.graphql      # Service types and operations
│   ├── environment.graphql  # Environment types and operations
│   ├── configuration.graphql # Configuration, ConfigSubstitution types and operations
│   └── shared_value.graphql # SharedValue, Revision types and operations
├── sql/                     # aiosql named query files
│   ├── services.sql
│   ├── environments.sql
│   ├── configurations.sql
│   └── shared_values.sql
├── data/                    # Data access layer
│   ├── __init__.py          # Re-exports: Configurations, Environments, Services, SharedValues
│   ├── utils.py             # aiosql loader, cursor pagination helpers
│   ├── services.py
│   ├── environments.py
│   ├── configurations.py
│   ├── shared_values.py
│   └── loaders.py           # DataLoader classes
└── resolvers/               # GraphQL resolvers
    ├── __init__.py          # create_gql(): schema creation, context setup, DI wiring
    ├── service.py
    ├── environment.py
    ├── configuration.py
    ├── shared_value.py
    └── scalars.py           # DateTime & JSON serialization

tests/
├── conftest.py              # Fixtures: pool, client, DB cleanup
├── utils.py                 # Shared test helpers: factories, parse_dt, nodes
├── test_services.py
├── test_environments.py
├── test_shared_values.py
└── test_configurations.py
```

---

## Coding Conventions

### Python

- **Python 3.12+** type syntax: `str | None`, `list[str] | None`.
- **Keyword-only arguments** on all data layer methods (`*` separator).
- **Plain dicts** as return types — no ORM models or dataclasses.
- Row conversion: `dict(row)` on asyncpg Records.
- `ValueError` for not-found / invalid state errors (resolvers catch and convert to GraphQL errors).

### GraphQL Schema (Schema-First)

- `schema.graphql` defines empty root types and `PageInfo` only.
- Domain files use `extend type Query` / `extend type Mutation` to co-locate operations with their types.
- Input types live in the same file as the mutation that uses them.
- Custom scalars: `DateTime` (ISO format), `JSON` (arbitrary object).
- Relay-style connections for lists: `*Connection`, `*Edge`, `PageInfo`.
- `includeArchived: Boolean` on list queries for archivable entities.
- `first` / `after` for cursor-based pagination.
- Flat naming: `createService`, `archiveEnvironment` — no nested namespace types.

### SQL (aiosql)

Named queries with operation suffixes:

| Suffix | Behavior                | Python usage                              |
|--------|-------------------------|-------------------------------------------|
| (none) | Multi-row; async generator | `[dict(r) async for r in queries.xxx()]` |
| `^`    | Single row; awaitable   | `row = await queries.xxx()`               |
| `!`    | Execute, no return      | `await queries.xxx()`                     |

Conventions:
- **Plural** table names: `services`, `configurations`.
- **snake_case** for all table and column names.
- Never `SELECT *` or `RETURNING *` — list columns explicitly.
- `IF NOT EXISTS` on DDL; `ON CONFLICT DO NOTHING` on seed inserts.
- Type casts (`::uuid`, `::boolean`, `::uuid[]`) required in conditional WHERE patterns.
- Soft delete filter: `(:include_archived::boolean OR archived_at IS NULL)`.
- Sentinel inclusion: `(:service_id::uuid IS NULL OR service_id = :service_id OR service_id = '00000000-0000-0000-0000-000000000000')`.
- Pagination: `ORDER BY id DESC` with `(:after_id::uuid IS NULL OR id < :after_id)` and `LIMIT :page_limit`.
- Trigram search via `%` operator and `similarity()` ordering with `pg_trgm`.
- ILIKE search for name/description fields on services and environments.

### Naming

- **Python**: snake_case for variables, functions, methods, modules.
- **GraphQL**: camelCase (auto-converted by Ariadne's `convert_names_case=True`).
- **Database**: snake_case columns, plural lowercase table names.
- **Files**: Domain-grouped. One SQL file, one data class, one resolver module, and one schema file per entity.

---

## Key Patterns

### Cursor-Based Pagination

```python
# data/utils.py
def build_connection(rows, cursor_key, limit, *, search=None) -> dict:
    has_next = len(rows) > limit
    nodes = rows[:limit]
    edges = [{"cursor": encode_cursor(str(row[cursor_key]), search=search), "node": row} for row in nodes]
    return {
        "edges": edges,
        "page_info": {"has_next_page": has_next, "end_cursor": edges[-1]["cursor"] if edges else None},
    }
```

- Fetch `limit + 1` rows. If the extra row exists, `has_next_page` is true.
- Cursors are base64-encoded JSON containing the row ID and optional search query.
- Search cursors include the search string — using a cursor from a different search raises `InvalidCursorError`.
- Use snake_case keys in dicts — Ariadne's `convert_names_case` maps to camelCase.

### Versioning with is_current

Configurations and shared value revisions use transactional version replacement:

```python
async with self.pool.acquire() as conn:
    async with conn.transaction():
        await queries.unset_current_configuration(conn, service_id=..., environment_id=...)
        row = await queries.create_configuration(conn, ...)
```

Pass `conn` (not `pool`) inside a transaction block. Pass `pool` directly for standalone queries.

### DataLoaders

Batch loading prevents N+1 on nested GraphQL fields:

```python
class ServiceLoader(DataLoader):
    async def batch_load_fn(self, ids):
        rows = [dict(r) async for r in queries.get_services_by_ids(self.pool, ids=list(ids))]
        by_id = {str(r["id"]): r for r in rows}
        return [by_id.get(str(i)) for i in ids]
```

Batch SQL queries use `ANY(:ids::uuid[])` for array parameters. Loaders are created fresh per request and accessed via `info.context["service_loader"].load(id)`.

### Resolver Structure

Each domain module exports a factory that returns a list of Ariadne bindables:

```python
class ServicesResolver:
    def __init__(self, services):
        self.services = services

    async def resolve_services(self, _obj, info, *, include_archived=False, search=None, first=None, after=None):
        return await self.services.get_services(...)

    async def resolve_service(self, _obj, info, *, id):
        return await info.context["service_loader"].load(id)

def get_service_resolvers(services) -> list:
    resolver = ServicesResolver(services)
    query = QueryType()
    mutation = MutationType()
    query.set_field("services", resolver.resolve_services)
    query.set_field("service", resolver.resolve_service)
    mutation.set_field("createService", resolver.resolve_create_service)
    ...
    return [query, mutation]
```

- Resolver signature: `async def resolve_X(self, _obj, info, **kwargs)`
- Field resolver signature: `async def resolve_X(self, obj, info)`
- With `convert_names_case=True`, kwargs arrive in snake_case.

### Soft Delete

- **GraphQL**: `includeArchived: Boolean` parameter on list queries.
- **SQL**: `(:include_archived::boolean OR archived_at IS NULL)`.
- **Archive**: `SET archived_at = now() WHERE ... AND archived_at IS NULL` (guard prevents re-archiving).
- **Unarchive**: `SET archived_at = NULL WHERE ... AND archived_at IS NOT NULL`.

### Dynaconf Configuration

```python
settings = Dynaconf(
    envvar_prefix="LANTERNA",
    settings_files=["settings.toml", ".secrets.toml"],
    environments=True,
    env_switcher="LANTERNA_ENV",
    default_env="default",
)
```

- Access: `settings.db.host`, `settings.server.port`.
- Override with env vars: `LANTERNA_DB__HOST=remote-host`.
- Switch environments: `LANTERNA_ENV=testing`.
- Non-default envs use `dynaconf_merge = true` to inherit from default.

---

## Testing

Tests run against a real PostgreSQL database (`lanterna_magica_test`), not mocks.

### Fixtures (conftest.py)

- `pool`: Creates/closes asyncpg connection pool.
- `client`: ASGI test client with pool and GraphQL schema initialized.
- `_clean_db` (autouse): Truncates all tables after each test, preserving sentinel rows. Deletion order respects foreign keys.

### Test Helpers (tests/utils.py)

Shared across test files:
- `parse_dt(iso_string)` — parses ISO datetime for comparison.
- `nodes(edges)` — extracts node list from connection edges.
- `create_service()`, `create_environment()`, `create_shared_value()`, `create_revision()` — factory helpers using minimal GraphQL mutations.

### Assertions (assertpy)

```python
from assertpy import assert_that

# Fluent assertions with descriptions
assert_that(svc["name"]).described_as("service name").is_equal_to("traefik")

# Date comparison
assert_that(parse_dt(updated["updatedAt"])).described_as("updatedAt advanced").is_after(
    parse_dt(svc["updatedAt"])
)

# List extraction
assert_that(nodes(edges)).described_as("services list").extracting("name").contains("traefik", "nginx")
```

- Use `described_as()` for assertion descriptions.
- Use `parse_dt()` + `is_after()` / `is_before()` for timestamp comparison.
- Use `extracting()` on lists of dicts, NOT on single dicts.
- Use bracket notation for single dict field access.

### Test Organization

- One test file per entity.
- GraphQL queries/mutations as module-level string constants.
- Local helpers (prefixed with `_`) for entity-specific factories that need full field sets.
- Shared helpers (no prefix) imported from `tests/utils.py`.
- `expect_errors=True` on `gql()` to test error paths.

---

## Gotchas

- **aiosql multi-row queries return async generators** — You cannot `await` them. Use `[dict(r) async for r in queries.xxx()]`.
- **aiosql pool vs conn** — Pass `pool` for standalone queries. Pass `conn` inside a `pool.acquire()` / `conn.transaction()` block. Passing `pool` inside a transaction defeats the transaction.
- **`convert_names_case` affects everything** — Ariadne converts camelCase to snake_case for resolver kwargs, input dict keys, and return dict keys. Use snake_case keys in Python dicts (`page_info`, `has_next_page`, `end_cursor`).
- **Ariadne `context_value` signature** — The callback receives two positional arguments `(request, data)`. Always use: `lambda request, _data=None: {...}`.
- **`psycopg2-binary` is required** — yoyo-migrations uses the synchronous psycopg2 driver internally.
- **JSONB codec** — `db.py` registers a JSONB codec on each connection so JSONB columns auto-serialize/deserialize. Exception: the `configurations.body` field arrives as a string from aiosql and must be parsed manually in the data layer via `json.loads()`.
- **assertpy `extracting()` on single dicts** — Iterates over dict keys (strings), not values. Only use on lists of dicts.
