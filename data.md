# Data Model

## Overview

Configuration is stored as JSON documents, versioned in place with an
`is_current` flag. Shared values use `"_"` as a placeholder in config
JSON bodies; a substitution table maps JSONPath locations to named
shared values. Substitutions are version-specific and re-created with
each new config version.

Scoping uses a flexible **dimensions** system. Rather than hard-coded
`service_id` / `environment_id` columns, every scoping axis (service,
environment, region, tenant, ...) is a **dimension kind**, and
individual entries (e.g. "traefik", "production") are **dimensions**.
Configurations and shared value revisions are scoped to an arbitrary
set of dimensions via junction tables, with a `scope_hash` for fast
uniqueness checks.

Unscoped records (global/base-layer) use the **base** dimension for
each kind. Every kind has exactly one dimension with `base = true`,
enforced by a partial unique index.

User references (`created_by`, `updated_by`, `archived_by`) default to
the sentinel UUID `00000000-0000-0000-0000-000000000000` until user
management is implemented.

---

## Tables

### dimension_typess

Registry of scoping axes. New types can be added at any time without
schema changes.

| Column     | Type        | Constraints              |
|------------|-------------|--------------------------|
| id         | uuid        | PK, default uuidv7()    |
| name       | text        | NOT NULL, UNIQUE         |
| priority   | integer     | NOT NULL, UNIQUE         |
| created_at | timestamptz | NOT NULL, default now()  |
| created_by  | uuid        | NOT NULL, default '00000000-...-000000000000'|
| archived_at | timestamptz | nullable                                     |
| archived_by | uuid        | nullable                                     |

Seeded with `service` and `environment`.

### dimensions

Unified table replacing the former `services` and `environments`
tables. Each row belongs to a kind; names are unique within a kind.

| Column      | Type        | Constraints                                  |
|-------------|-------------|----------------------------------------------|
| id          | uuid        | PK, default uuidv7()                         |
| type_id     | uuid        | FK -> dimension_types.id, NOT NULL           |
| name        | text        | NOT NULL                                     |
| description | text        |                                              |
| base        | boolean     | NOT NULL, default false                      |
| created_at  | timestamptz | NOT NULL, default now()                      |
| created_by  | uuid        | NOT NULL, default '00000000-...-000000000000'|
| updated_at  | timestamptz | NOT NULL, default now()                      |
| updated_by  | uuid        | NOT NULL, default '00000000-...-000000000000'|
| archived_at | timestamptz | nullable                                     |
| archived_by | uuid        | nullable                                     |

**Unique constraint:** `UNIQUE (type_id, name)`

**Partial unique index:**
`UNIQUE (type_id) WHERE base = true`
-- at most one base dimension per type.

**Trigram indexes:** GIN indexes on `name` and `description` for
ILIKE search.

Each type has exactly one `base` dimension (e.g. "global" for service,
"global" for environment) that serves as the default/unscoped value for
that axis.

### configurations

Versioned JSON config documents scoped to a set of dimensions.
Multiple rows may exist for a given scope; only one has
`is_current = true`.

| Column     | Type        | Constraints                                  |
|------------|-------------|----------------------------------------------|
| id         | uuid        | PK, default uuidv7()                         |
| scope_hash | uuid        | NOT NULL                                     |
| body       | jsonb       | NOT NULL                                     |
| is_current | boolean     | NOT NULL, default false                      |
| created_at | timestamptz | NOT NULL, default now()                      |
| created_by | uuid        | NOT NULL, default '00000000-...-000000000000'|

**Partial unique index:**
`UNIQUE (scope_hash) WHERE is_current = true`
-- at most one current config per scope.

**GIN index** on `body` for JSONB queries.

`scope_hash` is computed as `md5(sorted dimension IDs concatenated
with commas)::uuid`. Can be computed application-side or in SQL via
`md5(array_to_string(sort(dimension_ids), ','))::uuid`.

### configuration_scopes

Junction table linking a configuration to the dimensions that define
its scope.

| Column           | Type | Constraints                                   |
|------------------|------|-----------------------------------------------|
| configuration_id | uuid | FK -> configurations.id ON DELETE CASCADE, NOT NULL |
| dimension_id     | uuid | FK -> dimensions.id, NOT NULL                 |

**Primary key:** `(configuration_id, dimension_id)`

### config_substitutions

Maps a `"_"` placeholder location in a specific config version to a
shared value. Re-created when a new config version is created.

| Column           | Type        | Constraints                          |
|------------------|-------------|--------------------------------------|
| id               | uuid        | PK, default uuidv7()                |
| configuration_id | uuid        | FK -> configurations.id, NOT NULL    |
| jsonpath         | text        | NOT NULL                             |
| shared_value_id  | uuid        | FK -> shared_values.id, NOT NULL     |
| created_at       | timestamptz | NOT NULL, default now()              |
| created_by       | uuid        | NOT NULL, default '00000000-...-000000000000'|

**Unique constraint:** `UNIQUE (configuration_id, jsonpath)`

### shared_values

Named variables that can be referenced from configs via substitution.

| Column      | Type        | Constraints                                  |
|-------------|-------------|----------------------------------------------|
| id          | uuid        | PK, default uuidv7()                         |
| name        | text        | NOT NULL, UNIQUE                             |
| created_at  | timestamptz | NOT NULL, default now()                      |
| created_by  | uuid        | NOT NULL, default '00000000-...-000000000000'|
| updated_at  | timestamptz | NOT NULL, default now()                      |
| updated_by  | uuid        | NOT NULL, default '00000000-...-000000000000'|
| archived_at | timestamptz | nullable                                     |
| archived_by | uuid        | nullable                                     |

**Trigram index:** GIN index on `name` for similarity search.

### shared_value_revisions

Versioned values per shared_value+scope tuple. Multiple rows may exist
for a given tuple; only one has `is_current = true`.

| Column          | Type        | Constraints                                  |
|-----------------|-------------|----------------------------------------------|
| id              | uuid        | PK, default uuidv7()                         |
| shared_value_id | uuid        | FK -> shared_values.id, NOT NULL             |
| scope_hash      | uuid        | NOT NULL                                     |
| value           | jsonb       | NOT NULL                                     |
| is_current      | boolean     | NOT NULL, default false                      |
| created_at      | timestamptz | NOT NULL, default now()                      |
| created_by      | uuid        | NOT NULL, default '00000000-...-000000000000'|

**Partial unique index:**
`UNIQUE (shared_value_id, scope_hash) WHERE is_current = true`
-- at most one current value per shared_value+scope tuple.

### revision_scopes

Junction table linking a shared value revision to the dimensions that
define its scope.

| Column       | Type | Constraints                                            |
|--------------|------|--------------------------------------------------------|
| revision_id  | uuid | FK -> shared_value_revisions.id ON DELETE CASCADE, NOT NULL |
| dimension_id | uuid | FK -> dimensions.id, NOT NULL                          |

**Primary key:** `(revision_id, dimension_id)`
