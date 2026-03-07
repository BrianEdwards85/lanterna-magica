-- depends: 0007.add-pg-trgm-services-environments
-- Create dimension_types registry for scoping axes

CREATE TABLE IF NOT EXISTS dimension_types (
    id          uuid        PRIMARY KEY DEFAULT uuidv7(),
    name        text        NOT NULL UNIQUE,
    priority    integer     NOT NULL UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    archived_at timestamptz,
    archived_by uuid
);

ALTER TABLE dimension_types OWNER TO pg_database_owner;

-- Seed the two initial dimension types
INSERT INTO dimension_types (name, priority)
VALUES ('service', 1), ('environment', 2)
ON CONFLICT DO NOTHING;
