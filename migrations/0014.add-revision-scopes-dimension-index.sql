-- depends: 0013.seed-global-dimensions
-- Add index on revision_scopes(dimension_id) to support the scope resolution
-- query which joins this table on dimension_id.

CREATE INDEX IF NOT EXISTS ix_revision_scopes_dimension_id
    ON revision_scopes (dimension_id);
