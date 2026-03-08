-- depends: 0012.drop-services-environments
-- Create a base "global" dimension for every dimension type

INSERT INTO dimensions (type_id, name, description, base)
SELECT id, 'global', CONCAT('Default base for ', name, ' dimension'), true
FROM dimension_types
ON CONFLICT DO NOTHING;
