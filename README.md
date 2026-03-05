# lanterna-magica

Configuration management service for multi-service, multi-environment deployments.

## Problem

Managing configuration for services like Traefik, application instances, and their per-environment variants through docker-compose labels and scattered env files becomes unwieldy as the number of services and environments grows. Existing configuration management tools didn't fit the need for a lightweight, self-hosted solution with layered overrides and shared variables.

## What it does

lanterna-magica stores service configurations as versioned JSON documents scoped to a service+environment pair. When a new configuration is created for the same scope, the previous one is retained but marked non-current, providing a full audit trail.

Values shared across multiple configurations (API keys, domain names, database credentials) are managed as named shared values. Each shared value can have per-service and per-environment revisions, so a single logical value like `db_password` can resolve differently in production vs staging. Configurations reference shared values via JSONPath substitution rules, keeping a single source of truth for common values.

Both services and environments support a sentinel row (`_global`, UUID `00000000-...`) for unscoped configurations that apply broadly. Queries automatically include sentinel-scoped records alongside specifically-scoped ones.

## Stack

| Concern         | Library           | Notes                                           |
|-----------------|-------------------|-------------------------------------------------|
| HTTP server     | FastAPI           | ASGI with lifespan for startup/shutdown          |
| GraphQL         | Ariadne           | Schema-first; `convert_names_case=True`          |
| DB driver       | asyncpg           | Async PostgreSQL; pool shared via `app.state`    |
| SQL management  | aiosql            | Named queries from `.sql` files; asyncpg adapter |
| Batch loading   | aiodataloader     | Prevents N+1; fresh loaders per request          |
| Configuration   | Dynaconf          | Layered TOML + env vars + secrets                |
| Migrations      | yoyo-migrations   | Plain SQL files; auto-applied on startup         |
| Sync DB driver  | psycopg2-binary   | Required by yoyo (runs migrations synchronously) |
| ASGI server     | uvicorn           | With `[standard]` extras                         |
| Testing         | pytest            | With pytest-asyncio; tests against real Postgres |
| Assertions      | assertpy          | Fluent assertion syntax in tests                 |
| Linting         | Ruff              | Lint + format, target Python 3.12                |
| Package manager | uv                | Fast dependency resolution                       |

## Entities

- **Services** — named services (e.g. traefik, postgres). CRUD with soft delete (archive/unarchive).
- **Environments** — named environments (e.g. production, staging). CRUD with soft delete.
- **Configurations** — versioned JSON documents scoped to a service+environment pair. Only one is current per scope. Supports JSONPath substitution links to shared values.
- **Shared Values** — named shared variables (e.g. db_password, api_key). CRUD with soft delete and trigram search.
- **Shared Value Revisions** — versioned values scoped to a service+environment pair. Only one is current per scope.
- **Config Substitutions** — links a JSONPath in a configuration to a shared value for placeholder resolution.

## Development

```bash
uv sync --all-extras
uv run poe dev
```

Requires PostgreSQL with `uuidv7()` support. Connection settings are in `settings.toml`, overridable with `LANTERNA_DB__*` environment variables.

### Testing

```bash
uv run poe test
```

Tests run against a real `lanterna_magica_test` database, not mocks. Set `LANTERNA_ENV=testing` (handled automatically by conftest).

### API

GraphQL endpoint at `/graphql`. Health check at `/health`.

```bash
# Example: list services
curl -X POST http://localhost:8000/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query": "{ services { edges { node { id name } } } }"}'
```
