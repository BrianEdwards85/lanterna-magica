-- Recreate the old services and environments tables
CREATE TABLE IF NOT EXISTS services (
    id          uuid        PRIMARY KEY DEFAULT uuidv7(),
    name        text        NOT NULL UNIQUE,
    description text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    updated_at  timestamptz NOT NULL DEFAULT now(),
    updated_by  uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    archived_at timestamptz,
    archived_by uuid
);

ALTER TABLE services OWNER TO pg_database_owner;

INSERT INTO services (id, name, description)
VALUES ('00000000-0000-0000-0000-000000000000', '_global', 'Sentinel for unscoped configurations')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS environments (
    id          uuid        PRIMARY KEY DEFAULT uuidv7(),
    name        text        NOT NULL UNIQUE,
    description text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    updated_at  timestamptz NOT NULL DEFAULT now(),
    updated_by  uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    archived_at timestamptz,
    archived_by uuid
);

ALTER TABLE environments OWNER TO pg_database_owner;

INSERT INTO environments (id, name, description)
VALUES ('00000000-0000-0000-0000-000000000000', '_global', 'Sentinel for unscoped configurations')
ON CONFLICT DO NOTHING;

-- Restore trigram indexes
CREATE INDEX IF NOT EXISTS ix_services_name_trgm
    ON services USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_services_description_trgm
    ON services USING gin (description gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_environments_name_trgm
    ON environments USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_environments_description_trgm
    ON environments USING gin (description gin_trgm_ops);

-- Restore FK columns on configurations
ALTER TABLE configurations ADD COLUMN service_id uuid REFERENCES services(id);
ALTER TABLE configurations ADD COLUMN environment_id uuid REFERENCES environments(id);

-- Restore FK columns on shared_value_revisions
ALTER TABLE shared_value_revisions ADD COLUMN service_id uuid REFERENCES services(id);
ALTER TABLE shared_value_revisions ADD COLUMN environment_id uuid REFERENCES environments(id);

-- Note: data repopulation of service_id/environment_id columns from
-- junction tables would need to be done manually if rolling back.
