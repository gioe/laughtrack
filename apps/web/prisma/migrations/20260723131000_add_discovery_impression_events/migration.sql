CREATE TABLE "discovery_impression_events" (
    "event_id" UUID PRIMARY KEY,
    "entity_type" TEXT NOT NULL,
    "entity_id" INTEGER NOT NULL,
    "surface" TEXT NOT NULL,
    "policy_version" TEXT NOT NULL,
    "experiment_variant" TEXT NOT NULL,
    "rank" INTEGER NOT NULL,
    "impressed_at" TIMESTAMPTZ NOT NULL,
    "recorded_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "profile_id" TEXT,
    "anonymous_visitor_id" TEXT NOT NULL,
    CONSTRAINT "discovery_impression_events_profile_id_fkey"
        FOREIGN KEY ("profile_id") REFERENCES "user_profiles"("id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "discovery_impression_events_entity_type_check"
        CHECK ("entity_type" = 'show'),
    CONSTRAINT "discovery_impression_events_entity_id_check"
        CHECK ("entity_id" > 0),
    CONSTRAINT "discovery_impression_events_surface_check"
        CHECK ("surface" = 'near_you'),
    CONSTRAINT "discovery_impression_events_variant_check"
        CHECK ("experiment_variant" IN ('control', 'candidate')),
    CONSTRAINT "discovery_impression_events_rank_check"
        CHECK ("rank" BETWEEN 1 AND 1000),
    CONSTRAINT "discovery_impression_events_policy_version_check"
        CHECK ("policy_version" ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$'),
    CONSTRAINT "discovery_impression_events_anon_actor_check"
        CHECK (length("anonymous_visitor_id") BETWEEN 1 AND 128)
);

CREATE INDEX "discovery_impression_events_surface_variant_time_idx"
    ON "discovery_impression_events"("surface", "experiment_variant", "impressed_at");
CREATE INDEX "discovery_impression_events_entity_time_idx"
    ON "discovery_impression_events"("entity_type", "entity_id", "impressed_at");
CREATE INDEX "discovery_impression_events_profile_time_idx"
    ON "discovery_impression_events"("profile_id", "impressed_at");
CREATE INDEX "discovery_impression_events_anonymous_time_idx"
    ON "discovery_impression_events"("anonymous_visitor_id", "impressed_at");
CREATE INDEX "discovery_impression_events_recorded_at_idx"
    ON "discovery_impression_events"("recorded_at");

CREATE TABLE "discovery_engagement_events" (
    "event_id" UUID PRIMARY KEY,
    "impression_event_id" UUID NOT NULL,
    "engagement_type" TEXT NOT NULL,
    "engaged_at" TIMESTAMPTZ NOT NULL,
    "recorded_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT "discovery_engagement_events_impression_event_id_fkey"
        FOREIGN KEY ("impression_event_id") REFERENCES "discovery_impression_events"("event_id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "discovery_engagement_events_type_check"
        CHECK ("engagement_type" = 'show_detail')
);

CREATE INDEX "discovery_engagement_events_impression_type_idx"
    ON "discovery_engagement_events"("impression_event_id", "engagement_type");
CREATE INDEX "discovery_engagement_events_recorded_at_idx"
    ON "discovery_engagement_events"("recorded_at");

ALTER TABLE "ticket_purchase_click_events"
    ADD COLUMN "discovery_impression_event_id" UUID,
    ADD COLUMN "discovery_surface" TEXT,
    ADD COLUMN "discovery_policy_version" TEXT,
    ADD COLUMN "discovery_experiment_variant" TEXT,
    ADD COLUMN "discovery_rank" INTEGER,
    ADD CONSTRAINT "ticket_purchase_click_events_discovery_attribution_check"
        CHECK (
            (
                "discovery_impression_event_id" IS NULL
                AND "discovery_surface" IS NULL
                AND "discovery_policy_version" IS NULL
                AND "discovery_experiment_variant" IS NULL
                AND "discovery_rank" IS NULL
            )
            OR
            (
                "discovery_impression_event_id" IS NOT NULL
                AND "discovery_surface" IS NOT NULL
                AND "discovery_policy_version" IS NOT NULL
                AND "discovery_experiment_variant" IS NOT NULL
                AND "discovery_rank" BETWEEN 1 AND 1000
            )
        );

CREATE INDEX "ticket_purchase_click_events_discovery_impression_event_id_idx"
    ON "ticket_purchase_click_events"("discovery_impression_event_id");

CREATE OR REPLACE FUNCTION cleanup_old_discovery_events()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM discovery_impression_events
    WHERE recorded_at < NOW() - INTERVAL '13 months';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;
