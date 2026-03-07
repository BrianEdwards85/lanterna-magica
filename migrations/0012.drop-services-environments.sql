-- depends: 0011.create-scopes-and-hash
-- Drop old FK columns and old tables now that data is in dimensions

-- Drop old FK columns from configurations
ALTER TABLE configurations DROP COLUMN service_id;
ALTER TABLE configurations DROP COLUMN environment_id;

-- Drop old FK columns from shared_value_revisions
ALTER TABLE shared_value_revisions DROP COLUMN service_id;
ALTER TABLE shared_value_revisions DROP COLUMN environment_id;

-- Drop old trigram indexes (tables are about to be dropped, but be explicit)
DROP INDEX IF EXISTS ix_services_name_trgm;
DROP INDEX IF EXISTS ix_services_description_trgm;
DROP INDEX IF EXISTS ix_environments_name_trgm;
DROP INDEX IF EXISTS ix_environments_description_trgm;

-- Drop old tables
DROP TABLE IF EXISTS services CASCADE;
DROP TABLE IF EXISTS environments CASCADE;
