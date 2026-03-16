-- depends: 0009.create-dimensions
-- Create junction tables and add scope_hash columns

-- Junction: configuration -> dimensions
CREATE TABLE IF NOT EXISTS configuration_scopes (
    configuration_id uuid NOT NULL REFERENCES configurations(id) ON DELETE CASCADE,
    dimension_id     uuid NOT NULL REFERENCES dimensions(id),
    PRIMARY KEY (configuration_id, dimension_id)
);

ALTER TABLE configuration_scopes OWNER TO pg_database_owner;

-- Junction: shared_value_revision -> dimensions
CREATE TABLE IF NOT EXISTS revision_scopes (
    revision_id  uuid NOT NULL REFERENCES shared_value_revisions(id) ON DELETE CASCADE,
    dimension_id uuid NOT NULL REFERENCES dimensions(id),
    PRIMARY KEY (revision_id, dimension_id)
);

ALTER TABLE revision_scopes OWNER TO pg_database_owner;

-- Add scope_hash to configurations
ALTER TABLE configurations ADD COLUMN scope_hash uuid NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';
ALTER TABLE configurations ALTER COLUMN scope_hash DROP DEFAULT;

-- Add scope_hash to shared_value_revisions
ALTER TABLE shared_value_revisions ADD COLUMN scope_hash uuid NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';
ALTER TABLE shared_value_revisions ALTER COLUMN scope_hash DROP DEFAULT;

-- Replace old unique indexes with scope_hash-based ones
DROP INDEX IF EXISTS uix_configurations_current;
CREATE UNIQUE INDEX uix_configurations_current
    ON configurations (scope_hash) WHERE is_current = true;

DROP INDEX IF EXISTS uix_shared_value_revisions_current;
CREATE UNIQUE INDEX uix_shared_value_revisions_current
    ON shared_value_revisions (shared_value_id, scope_hash) WHERE is_current = true;
