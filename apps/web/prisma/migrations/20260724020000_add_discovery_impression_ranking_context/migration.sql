-- Preserve request-time ranking context so pilot evaluation does not infer
-- assignment, exploration, geography, or actionability from mutable data.
-- Columns remain nullable because historical impressions predate this context.
ALTER TABLE discovery_impression_events
    ADD COLUMN assignment_eligible BOOLEAN,
    ADD COLUMN assignment_reason TEXT,
    ADD COLUMN exploration_selected BOOLEAN,
    ADD COLUMN distance_miles DOUBLE PRECISION,
    ADD COLUMN max_distance_miles DOUBLE PRECISION,
    ADD COLUMN availability_at_impression TEXT,
    ADD COLUMN feature_version TEXT;

ALTER TABLE discovery_impression_events
    ADD CONSTRAINT discovery_impressions_assignment_reason_check
        CHECK (
            assignment_reason IS NULL
            OR assignment_reason IN (
                'stable_actor_assignment',
                'cookieless_bootstrap'
            )
        ),
    ADD CONSTRAINT discovery_impressions_availability_check
        CHECK (
            availability_at_impression IS NULL
            OR availability_at_impression IN (
                'available',
                'unknown',
                'unavailable'
            )
        ),
    ADD CONSTRAINT discovery_impressions_distance_check
        CHECK (
            (distance_miles IS NULL OR distance_miles >= 0)
            AND (max_distance_miles IS NULL OR max_distance_miles > 0)
        );

CREATE INDEX discovery_impressions_assignment_variant_time_idx
    ON discovery_impression_events (
        assignment_eligible,
        experiment_variant,
        impressed_at
    );
