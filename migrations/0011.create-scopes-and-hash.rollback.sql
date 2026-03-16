-- Restore old unique indexes
DROP INDEX IF EXISTS uix_configurations_current;
CREATE UNIQUE INDEX uix_configurations_current
    ON configurations (service_id, environment_id) WHERE is_current = true;

DROP INDEX IF EXISTS uix_shared_value_revisions_current;
CREATE UNIQUE INDEX uix_shared_value_revisions_current
    ON shared_value_revisions (shared_value_id, service_id, environment_id) WHERE is_current = true;

-- Drop scope_hash columns
ALTER TABLE configurations DROP COLUMN IF EXISTS scope_hash;
ALTER TABLE shared_value_revisions DROP COLUMN IF EXISTS scope_hash;

-- Drop junction tables
DROP TABLE IF EXISTS revision_scopes CASCADE;
DROP TABLE IF EXISTS configuration_scopes CASCADE;
