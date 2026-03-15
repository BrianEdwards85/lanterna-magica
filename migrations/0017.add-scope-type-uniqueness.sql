-- depends: 0016.add-configurations-archived-at
-- Purge invalid scope data and add type_id uniqueness constraints

-- Step 1: Delete configurations where any two scoped dimensions share a type_id.
-- config_substitutions cascade via FK on configurations.id.
-- configuration_scopes cascade via FK on configurations.id.
DELETE FROM configurations
WHERE id IN (
    SELECT cs.configuration_id
    FROM configuration_scopes cs
    JOIN dimensions d ON d.id = cs.dimension_id
    GROUP BY cs.configuration_id, d.type_id
    HAVING COUNT(*) > 1
);

-- Step 2: Delete shared_value_revisions where any two scoped dimensions share a type_id.
-- revision_scopes cascade via FK on shared_value_revisions.id.
DELETE FROM shared_value_revisions
WHERE id IN (
    SELECT rs.revision_id
    FROM revision_scopes rs
    JOIN dimensions d ON d.id = rs.dimension_id
    GROUP BY rs.revision_id, d.type_id
    HAVING COUNT(*) > 1
);

-- Step 3: Add type_id to configuration_scopes (nullable first, then backfill, then NOT NULL).
ALTER TABLE configuration_scopes ADD COLUMN type_id uuid;
UPDATE configuration_scopes cs
    SET type_id = d.type_id
    FROM dimensions d
    WHERE d.id = cs.dimension_id;
ALTER TABLE configuration_scopes ALTER COLUMN type_id SET NOT NULL;

-- Step 4: Add type_id to revision_scopes (nullable first, then backfill, then NOT NULL).
ALTER TABLE revision_scopes ADD COLUMN type_id uuid;
UPDATE revision_scopes rs
    SET type_id = d.type_id
    FROM dimensions d
    WHERE d.id = rs.dimension_id;
ALTER TABLE revision_scopes ALTER COLUMN type_id SET NOT NULL;

-- Step 5: Add FK constraints referencing dimension_types(id).
ALTER TABLE configuration_scopes
    ADD CONSTRAINT fk_configuration_scopes_type_id
    FOREIGN KEY (type_id) REFERENCES dimension_types(id);

ALTER TABLE revision_scopes
    ADD CONSTRAINT fk_revision_scopes_type_id
    FOREIGN KEY (type_id) REFERENCES dimension_types(id);

-- Step 6: Add UNIQUE constraints — one dimension per type per configuration/revision.
ALTER TABLE configuration_scopes
    ADD CONSTRAINT uq_configuration_scopes_configuration_type
    UNIQUE (configuration_id, type_id);

ALTER TABLE revision_scopes
    ADD CONSTRAINT uq_revision_scopes_revision_type
    UNIQUE (revision_id, type_id);
