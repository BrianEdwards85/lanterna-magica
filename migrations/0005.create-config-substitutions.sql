-- depends: 0003.create-configurations
-- depends: 0004.create-shared-values
-- Create config_substitutions linking config placeholders to shared values

CREATE TABLE IF NOT EXISTS config_substitutions (
    id               uuid        PRIMARY KEY DEFAULT uuidv7(),
    configuration_id uuid        NOT NULL REFERENCES configurations(id),
    jsonpath         text        NOT NULL,
    shared_value_id  uuid        NOT NULL REFERENCES shared_values(id),
    created_at       timestamptz NOT NULL DEFAULT now(),
    created_by       uuid        NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'
);

ALTER TABLE config_substitutions OWNER TO pg_database_owner;

CREATE UNIQUE INDEX IF NOT EXISTS uix_config_substitutions_path
    ON config_substitutions (configuration_id, jsonpath);
