DELETE FROM discovery_rail_policy_entries
WHERE rail_key IN (
    'rare_returns',
    'only_chance_nearby',
    'newly_added',
    'catch_them_early'
);

DELETE FROM discovery_rail_catalog
WHERE key IN (
    'rare_returns',
    'only_chance_nearby',
    'newly_added',
    'catch_them_early'
);

UPDATE discovery_rail_policy_entries
SET
    rotation_pool = NULL,
    weight = 1
WHERE rail_key IN ('just_passing_through', 'starting_to_buzz');

UPDATE discovery_rail_catalog
SET
    label = 'Rarely nearby',
    catalog_version = 4,
    updated_at = NOW()
WHERE key = 'just_passing_through';

UPDATE discovery_rail_catalog
SET
    label = 'Shows gaining momentum',
    catalog_version = 4,
    updated_at = NOW()
WHERE key = 'starting_to_buzz';

UPDATE discovery_rail_platform_policies
SET
    catalog_version = 4,
    policy_version = policy_version + 1,
    updated_at = NOW()
WHERE catalog_version < 4;
