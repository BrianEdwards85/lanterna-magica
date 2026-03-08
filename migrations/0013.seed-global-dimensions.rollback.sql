-- Rollback: remove base "global" dimensions
DELETE FROM dimensions WHERE name = 'global' AND base = true;
