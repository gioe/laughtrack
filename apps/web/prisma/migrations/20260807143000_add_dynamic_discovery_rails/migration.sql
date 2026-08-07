INSERT INTO discovery_rail_catalog (
    key,
    label,
    content_kind,
    requires_auth,
    supported_platforms,
    catalog_version
)
VALUES
    ('just_passing_through', 'Just passing through', 'show', false, '["web", "ios", "android"]'::jsonb, 2),
    ('rare_returns', 'Rarely in town / Back after a while', 'show', false, '["web", "ios", "android"]'::jsonb, 2),
    ('only_chance_nearby', 'Only chance nearby', 'show', false, '["web", "ios", "android"]'::jsonb, 2),
    ('newly_added', 'Newly added', 'show', false, '["web", "ios", "android"]'::jsonb, 2),
    ('starting_to_buzz', 'Starting to buzz', 'show', false, '["web", "ios", "android"]'::jsonb, 2),
    ('catch_them_early', 'Catch them early', 'show', false, '["web", "ios", "android"]'::jsonb, 2),
    ('from_your_podcasts', 'From your podcasts', 'show', true, '["web", "ios", "android"]'::jsonb, 2),
    ('stacked_lineups', 'Stacked lineups', 'show', false, '["web", "ios", "android"]'::jsonb, 2),
    ('because_you_follow_them', 'Because you follow them', 'show', true, '["web", "ios", "android"]'::jsonb, 2)
ON CONFLICT (key) DO NOTHING;

WITH dynamic_entries (rail_key, slot_offset, rotation_pool) AS (
    VALUES
        ('just_passing_through', 1, 'touring_scarcity'),
        ('only_chance_nearby', 1, 'touring_scarcity'),
        ('rare_returns', 1, 'touring_scarcity'),
        ('catch_them_early', 2, 'fresh_and_rising'),
        ('newly_added', 2, 'fresh_and_rising'),
        ('starting_to_buzz', 2, 'fresh_and_rising'),
        ('because_you_follow_them', 3, 'affinity'),
        ('from_your_podcasts', 3, 'affinity'),
        ('stacked_lineups', 3, 'affinity')
), current_positions AS (
    SELECT
        policy.platform,
        COALESCE(MAX(entry.position), -1) AS max_position
    FROM discovery_rail_platform_policies policy
    LEFT JOIN discovery_rail_policy_entries entry
        ON entry.platform = policy.platform
    GROUP BY policy.platform
)
INSERT INTO discovery_rail_policy_entries (
    platform,
    rail_key,
    enabled,
    position,
    rotation_pool,
    weight
)
SELECT
    current_positions.platform,
    dynamic_entries.rail_key,
    true,
    current_positions.max_position + dynamic_entries.slot_offset,
    dynamic_entries.rotation_pool,
    1
FROM current_positions
CROSS JOIN dynamic_entries
ON CONFLICT (platform, rail_key) DO NOTHING;

UPDATE discovery_rail_platform_policies
SET
    catalog_version = 2,
    policy_version = policy_version + 1,
    updated_at = NOW()
WHERE catalog_version < 2;
