-- depends: 0001.create-services
-- depends: 0002.create-environments
-- Create shared_values and shared_value_revisions tables

CREATE TABLE IF NOT EXISTS shared_values (
    id          uuid        PRIMARY KEY DEFAULT uuidv7(),
    name        text        NOT NULL UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    updated_at  timestamptz NOT NULL DEFAULT now(),
    updated_by  uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    archived_at timestamptz,
    archived_by uuid
);

ALTER TABLE shared_values OWNER TO pg_database_owner;

CREATE TABLE IF NOT EXISTS shared_value_revisions (
    id              uuid        PRIMARY KEY DEFAULT uuidv7(),
    shared_value_id uuid        NOT NULL REFERENCES shared_values(id),
    service_id      uuid        NOT NULL REFERENCES services(id),
    environment_id  uuid        NOT NULL REFERENCES environments(id),
    value           jsonb       NOT NULL,
    is_current      boolean     NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now(),
    created_by      uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'
);

ALTER TABLE shared_value_revisions OWNER TO pg_database_owner;

CREATE UNIQUE INDEX IF NOT EXISTS uix_shared_value_revisions_current
    ON shared_value_revisions (shared_value_id, service_id, environment_id)
    WHERE is_current = true;
