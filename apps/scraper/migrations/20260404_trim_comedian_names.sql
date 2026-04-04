-- TASK-926: Trim leading/trailing whitespace from existing comedian names.
-- 64 records have whitespace that causes deny-list exact-match misses.
UPDATE comedians SET name = trim(name) WHERE name != trim(name);
