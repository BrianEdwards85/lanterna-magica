-- Create services table with sentinel row for unscoped records

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
