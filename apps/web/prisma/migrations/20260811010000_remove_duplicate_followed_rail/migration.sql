-- Retire the duplicate personalized rail. The fixed followed-comedian rail is
-- the canonical home-feed surface for shows from favorite comedians.
DELETE FROM discovery_rail_policy_entries
WHERE rail_key = 'because_you_follow_them';

DELETE FROM discovery_rail_catalog
WHERE key = 'because_you_follow_them';

-- The remaining affinity rail no longer rotates against another candidate.
UPDATE discovery_rail_policy_entries
SET rotation_pool = NULL,
    weight = 1
WHERE rail_key = 'from_your_podcasts';

UPDATE discovery_rail_catalog
SET catalog_version = 5,
    updated_at = NOW()
WHERE key = 'from_your_podcasts';

UPDATE discovery_rail_platform_policies
SET catalog_version = 5,
    policy_version = policy_version + 1,
    updated_at = NOW()
WHERE catalog_version < 5;

-- Retired-surface telemetry cannot satisfy the replacement constraint.
DELETE FROM discovery_impression_events
WHERE surface = 'because_you_follow_them';

ALTER TABLE discovery_impression_events
    DROP CONSTRAINT discovery_impression_events_surface_check;

ALTER TABLE discovery_impression_events
    ADD CONSTRAINT discovery_impression_events_surface_check CHECK (
        surface IN (
            'near_you',
            'shows_tonight',
            'followed_comedian_shows',
            'trending_this_week',
            'nearby_shows',
            'just_passing_through',
            'rare_returns',
            'only_chance_nearby',
            'newly_added',
            'starting_to_buzz',
            'catch_them_early',
            'from_your_podcasts',
            'stacked_lineups'
        )
    );
