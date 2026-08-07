ALTER TABLE discovery_impression_events
    DROP CONSTRAINT discovery_impression_events_surface_check,
    DROP CONSTRAINT discovery_impression_events_variant_check;

ALTER TABLE discovery_impression_events
    ADD CONSTRAINT discovery_impression_events_surface_check
        CHECK (
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
                'stacked_lineups',
                'because_you_follow_them'
            )
        ),
    ADD CONSTRAINT discovery_impression_events_variant_check
        CHECK (
            (surface = 'near_you' AND experiment_variant IN ('control', 'candidate'))
            OR
            (surface <> 'near_you' AND experiment_variant = 'server_directed')
        );
