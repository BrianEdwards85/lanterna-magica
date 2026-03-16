-- depends: 0014.add-revision-scopes-dimension-index
-- Add index on configuration_scopes(dimension_id) to support the scope resolution
-- query which joins this table on dimension_id.

CREATE INDEX IF NOT EXISTS ix_configuration_scopes_dimension_id
    ON configuration_scopes (dimension_id);
