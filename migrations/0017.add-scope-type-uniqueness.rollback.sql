-- Drop UNIQUE constraints
ALTER TABLE configuration_scopes DROP CONSTRAINT IF EXISTS uq_configuration_scopes_configuration_type;
ALTER TABLE revision_scopes DROP CONSTRAINT IF EXISTS uq_revision_scopes_revision_type;

-- Drop FK constraints
ALTER TABLE configuration_scopes DROP CONSTRAINT IF EXISTS fk_configuration_scopes_type_id;
ALTER TABLE revision_scopes DROP CONSTRAINT IF EXISTS fk_revision_scopes_type_id;

-- Drop type_id columns
ALTER TABLE configuration_scopes DROP COLUMN IF EXISTS type_id;
ALTER TABLE revision_scopes DROP COLUMN IF EXISTS type_id;
