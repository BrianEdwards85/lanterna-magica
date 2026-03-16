-- depends: 0008.create-dimension-types
-- Create unified dimensions table replacing services and environments

CREATE TABLE IF NOT EXISTS dimensions (
    id          uuid        PRIMARY KEY DEFAULT uuidv7(),
    type_id     uuid        NOT NULL REFERENCES dimension_types(id),
    name        text        NOT NULL,
    description text,
    base        boolean     NOT NULL DEFAULT false,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    updated_at  timestamptz NOT NULL DEFAULT now(),
    updated_by  uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    archived_at timestamptz,
    archived_by uuid
);

ALTER TABLE dimensions OWNER TO pg_database_owner;

-- Names are unique within a type
CREATE UNIQUE INDEX IF NOT EXISTS uix_dimensions_type_name
    ON dimensions (type_id, name);

-- At most one base dimension per type
CREATE UNIQUE INDEX IF NOT EXISTS uix_dimensions_base_per_type
    ON dimensions (type_id) WHERE base = true;

-- Trigram indexes for ILIKE search
CREATE INDEX IF NOT EXISTS ix_dimensions_name_trgm
    ON dimensions USING gin (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_dimensions_description_trgm
    ON dimensions USING gin (description gin_trgm_ops);
