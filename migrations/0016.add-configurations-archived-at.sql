-- depends: 0015.add-configuration-scopes-dimension-index
-- Add soft-delete support to configurations table

ALTER TABLE configurations ADD COLUMN archived_at timestamptz;
