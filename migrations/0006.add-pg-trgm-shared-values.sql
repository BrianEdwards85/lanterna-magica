-- depends: 0004.create-shared-values
-- Enable pg_trgm and add trigram index on shared_values.name

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS ix_shared_values_name_trgm
    ON shared_values USING gin (name gin_trgm_ops);
