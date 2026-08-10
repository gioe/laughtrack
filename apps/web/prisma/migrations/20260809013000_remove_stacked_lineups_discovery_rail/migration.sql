DELETE FROM discovery_rail_policy_entries
WHERE rail_key = 'stacked_lineups';

DELETE FROM discovery_rail_catalog
WHERE key = 'stacked_lineups';

UPDATE discovery_rail_platform_policies
SET
    catalog_version = 3,
    policy_version = policy_version + 1,
    updated_at = NOW()
WHERE catalog_version < 3;
