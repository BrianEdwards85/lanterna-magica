-- depends: 0017.add-scope-type-uniqueness
-- Create tables for the config disk output system

-- Output definitions
CREATE TABLE IF NOT EXISTS outputs (
    id            uuid        PRIMARY KEY DEFAULT uuidv7(),
    path_template text        NOT NULL,
    format        text        NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    created_by    uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    updated_at    timestamptz NOT NULL DEFAULT now(),
    updated_by    uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    archived_at   timestamptz,
    archived_by   uuid,
    CONSTRAINT chk_outputs_format CHECK (format IN ('json', 'yml', 'toml', 'env'))
);

ALTER TABLE outputs OWNER TO pg_database_owner;

-- Junction: output -> dimensions (dimension values assigned to an output)
CREATE TABLE IF NOT EXISTS output_dimensions (
    output_id    uuid NOT NULL REFERENCES outputs(id) ON DELETE CASCADE,
    dimension_id uuid NOT NULL REFERENCES dimensions(id),
    PRIMARY KEY (output_id, dimension_id)
);

ALTER TABLE output_dimensions OWNER TO pg_database_owner;

-- Per-combination write results
CREATE TABLE IF NOT EXISTS output_results (
    id         uuid        PRIMARY KEY DEFAULT uuidv7(),
    output_id  uuid        NOT NULL REFERENCES outputs(id),
    scope_hash uuid        NOT NULL,
    path       text        NOT NULL,
    content    text        NOT NULL,
    succeeded  boolean     NOT NULL,
    error      text,
    written_at timestamptz NOT NULL DEFAULT now(),
    written_by uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    UNIQUE (output_id, scope_hash)
);

ALTER TABLE output_results OWNER TO pg_database_owner;
