-- depends: 0001.create-services
-- depends: 0002.create-environments
-- Create configurations table for versioned JSON config documents

CREATE TABLE IF NOT EXISTS configurations (
    id             uuid        PRIMARY KEY DEFAULT uuidv7(),
    service_id     uuid        NOT NULL REFERENCES services(id),
    environment_id uuid        NOT NULL REFERENCES environments(id),
    body           jsonb       NOT NULL,
    is_current     boolean     NOT NULL DEFAULT false,
    created_at     timestamptz NOT NULL DEFAULT now(),
    created_by     uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'
);

ALTER TABLE configurations OWNER TO pg_database_owner;

CREATE UNIQUE INDEX IF NOT EXISTS uix_configurations_current
    ON configurations (service_id, environment_id)
    WHERE is_current = true;

CREATE INDEX IF NOT EXISTS ix_configurations_body
    ON configurations USING gin (body);
