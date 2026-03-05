-- depends: 0006.add-pg-trgm-shared-values
-- Add trigram indexes on services and environments for ILIKE search

CREATE INDEX IF NOT EXISTS ix_services_name_trgm
    ON services USING gin (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_services_description_trgm
    ON services USING gin (description gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_environments_name_trgm
    ON environments USING gin (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_environments_description_trgm
    ON environments USING gin (description gin_trgm_ops);
