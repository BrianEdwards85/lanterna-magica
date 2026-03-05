# Data Model

## Overview

Configuration is stored as JSON documents, versioned in place with an
`is_current` flag. Shared values use `"_"` as a placeholder in config
JSON bodies; a substitution table maps JSONPath locations to named
shared values. Substitutions are version-specific and re-created with
each new config version.

Unscoped records (global/base-layer) use a sentinel UUID
`00000000-0000-0000-0000-000000000000` for `service_id` and/or
`environment_id` rather than NULL.

User references (`created_by`, `updated_by`, `archived_by`) default to
the sentinel UUID `00000000-0000-0000-0000-000000000000` until user
management is implemented.

---

## Tables

### services

| Column      | Type        | Constraints                                  |
|-------------|-------------|----------------------------------------------|
| id          | uuid        | PK, default uuidv7()                         |
| name        | text        | NOT NULL, UNIQUE                             |
| description | text        |                                              |
| created_at  | timestamptz | NOT NULL, default now()                      |
| created_by  | uuid        | NOT NULL, default '00000000-…-000000000000'  |
| updated_at  | timestamptz | NOT NULL, default now()                      |
| updated_by  | uuid        | NOT NULL, default '00000000-…-000000000000'  |
| archived_at | timestamptz | nullable                                     |
| archived_by | uuid        | nullable                                     |

### environments

| Column      | Type        | Constraints                                  |
|-------------|-------------|----------------------------------------------|
| id          | uuid        | PK, default uuidv7()                         |
| name        | text        | NOT NULL, UNIQUE                             |
| description | text        |                                              |
| created_at  | timestamptz | NOT NULL, default now()                      |
| created_by  | uuid        | NOT NULL, default '00000000-…-000000000000'  |
| updated_at  | timestamptz | NOT NULL, default now()                      |
| updated_by  | uuid        | NOT NULL, default '00000000-…-000000000000'  |
| archived_at | timestamptz | nullable                                     |
| archived_by | uuid        | nullable                                     |

### configurations

Versioned JSON config documents per service+environment pair. Multiple
rows may exist for a given pair; only one has `is_current = true`.

| Column         | Type        | Constraints                                  |
|----------------|-------------|----------------------------------------------|
| id             | uuid        | PK, default uuidv7()                         |
| service_id     | uuid        | FK → services.id, NOT NULL                   |
| environment_id | uuid        | FK → environments.id, NOT NULL               |
| body           | jsonb       | NOT NULL                                     |
| is_current     | boolean     | NOT NULL, default false                      |
| created_at     | timestamptz | NOT NULL, default now()                      |
| created_by     | uuid        | NOT NULL, default '00000000-…-000000000000'  |

**Partial unique index:**
`UNIQUE (service_id, environment_id) WHERE is_current = true`
— at most one current config per service+environment pair.

### config_substitutions

Maps a `"_"` placeholder location in a specific config version to a
shared value. Re-created when a new config version is created.

| Column          | Type        | Constraints                          |
|-----------------|-------------|--------------------------------------|
| id              | uuid        | PK, default uuidv7()                 |
| configuration_id| uuid        | FK → configurations.id, NOT NULL     |
| jsonpath        | text        | NOT NULL                             |
| shared_value_id | uuid        | FK → shared_values.id, NOT NULL      |
| created_at      | timestamptz | NOT NULL, default now()              |
| created_by     | uuid        | NOT NULL, default '00000000-…-000000000000'  |

**Unique constraint:** `UNIQUE (configuration_id, jsonpath)`

### shared_values

Named variables that can be referenced from configs via substitution.

| Column      | Type        | Constraints                                  |
|-------------|-------------|----------------------------------------------|
| id          | uuid        | PK, default uuidv7()                         |
| name        | text        | NOT NULL, UNIQUE                             |
| created_at  | timestamptz | NOT NULL, default now()                      |
| created_by  | uuid        | NOT NULL, default '00000000-…-000000000000'  |
| updated_at  | timestamptz | NOT NULL, default now()                      |
| updated_by  | uuid        | NOT NULL, default '00000000-…-000000000000'  |
| archived_at | timestamptz | nullable                                     |
| archived_by | uuid        | nullable                                     |

### shared_value_revisions

Versioned values per shared_value+service+environment tuple. Multiple
rows may exist for a given tuple; only one has `is_current = true`.

| Column          | Type        | Constraints                                  |
|-----------------|-------------|----------------------------------------------|
| id              | uuid        | PK, default uuidv7()                         |
| shared_value_id | uuid        | FK → shared_values.id, NOT NULL              |
| service_id      | uuid        | FK → services.id, NOT NULL                   |
| environment_id  | uuid        | FK → environments.id, NOT NULL               |
| value           | jsonb       | NOT NULL                                     |
| is_current      | boolean     | NOT NULL, default false                      |
| created_at      | timestamptz | NOT NULL, default now()                      |
| created_by      | uuid        | NOT NULL, default '00000000-…-000000000000'  |

**Partial unique index:**
`UNIQUE (shared_value_id, service_id, environment_id) WHERE is_current = true`
— at most one current value per shared_value+service+environment tuple.
