# lanterna-magica

Configuration management service for multi-service, multi-environment deployments.

## Problem

Managing configuration for services like Traefik, application instances, and their per-environment variants through docker-compose labels and scattered env files becomes unwieldy as the number of services and environments grows. Existing configuration management tools didn't fit the need for a lightweight, self-hosted solution with layered overrides and shared variables.

## What it does

lanterna-magica stores service configurations as JSON documents with layered specificity. A configuration can be scoped globally, to a specific service, to a specific environment, or to a service+environment pair. At resolution time, layers are deep-merged so that more specific configurations override less specific ones without duplicating the entire document.

Values that are shared across multiple configurations (API keys, domain names, email addresses) are managed as named shared variables. Configurations reference these via placeholder substitution, keeping a single source of truth for common values. Shared variables support the same per-service and per-environment scoping.

Both configurations and shared values are versioned — full document snapshots are retained so that any prior state can be inspected or restored.

## Stack

| Concern        | Library           |
|----------------|-------------------|
| HTTP / REST    | FastAPI           |
| GraphQL        | Ariadne           |
| DB driver      | asyncpg           |
| Migrations     | yoyo-migrations   |
| Configuration  | Dynaconf          |
| ASGI server    | uvicorn           |
| Package manager| uv                |

## Development

```
uv sync --all-extras
uv run poe dev
```

Requires a PostgreSQL 18 database. Connection settings are in `settings.toml`, overridable with `LANTERNA_DB__*` environment variables.
