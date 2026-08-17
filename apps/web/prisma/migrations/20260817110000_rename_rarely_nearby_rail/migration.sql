UPDATE discovery_rail_catalog
SET
    label = 'Here for a Limited Time',
    catalog_version = 6,
    updated_at = NOW()
WHERE key = 'just_passing_through';

UPDATE discovery_rail_platform_policies
SET
    catalog_version = 6,
    policy_version = policy_version + 1,
    updated_at = NOW()
WHERE catalog_version < 6;
