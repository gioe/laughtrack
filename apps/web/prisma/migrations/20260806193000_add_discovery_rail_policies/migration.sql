CREATE TABLE "discovery_rail_catalog" (
    "key" TEXT PRIMARY KEY,
    "label" TEXT NOT NULL,
    "content_kind" TEXT NOT NULL,
    "requires_auth" BOOLEAN NOT NULL DEFAULT false,
    "supported_platforms" JSONB NOT NULL DEFAULT '[]'::jsonb,
    "catalog_version" INTEGER NOT NULL DEFAULT 1,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT "discovery_rail_catalog_version_check"
        CHECK ("catalog_version" >= 1),
    CONSTRAINT "discovery_rail_catalog_platforms_check"
        CHECK (
            jsonb_typeof("supported_platforms") = 'array'
            AND "supported_platforms" <@ '["web", "ios", "android"]'::jsonb
        )
);

CREATE INDEX "discovery_rail_catalog_catalog_version_idx"
    ON "discovery_rail_catalog"("catalog_version");

CREATE TABLE "discovery_rail_platform_policies" (
    "platform" TEXT PRIMARY KEY,
    "policy_version" INTEGER NOT NULL DEFAULT 1,
    "catalog_version" INTEGER NOT NULL DEFAULT 1,
    "cycle_cadence_hours" INTEGER NOT NULL DEFAULT 24,
    "updated_by_profile_id" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT "discovery_rail_platform_policies_platform_check"
        CHECK ("platform" IN ('web', 'ios', 'android')),
    CONSTRAINT "discovery_rail_platform_policies_policy_version_check"
        CHECK ("policy_version" >= 1),
    CONSTRAINT "discovery_rail_platform_policies_catalog_version_check"
        CHECK ("catalog_version" >= 1),
    CONSTRAINT "discovery_rail_platform_policies_cadence_check"
        CHECK ("cycle_cadence_hours" >= 1),
    CONSTRAINT "discovery_rail_platform_policies_updated_by_profile_id_fkey"
        FOREIGN KEY ("updated_by_profile_id") REFERENCES "user_profiles"("id")
        ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX "discovery_rail_platform_policies_updated_by_profile_id_idx"
    ON "discovery_rail_platform_policies"("updated_by_profile_id");

CREATE TABLE "discovery_rail_policy_entries" (
    "platform" TEXT NOT NULL,
    "rail_key" TEXT NOT NULL,
    "enabled" BOOLEAN NOT NULL DEFAULT true,
    "position" INTEGER NOT NULL,
    "rotation_pool" TEXT,
    "weight" INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT "discovery_rail_policy_entries_pkey"
        PRIMARY KEY ("platform", "rail_key"),
    CONSTRAINT "discovery_rail_policy_entries_position_check"
        CHECK ("position" >= 0),
    CONSTRAINT "discovery_rail_policy_entries_rotation_pool_check"
        CHECK ("rotation_pool" IS NULL OR length(btrim("rotation_pool")) > 0),
    CONSTRAINT "discovery_rail_policy_entries_weight_check"
        CHECK ("weight" BETWEEN 1 AND 100),
    CONSTRAINT "discovery_rail_policy_entries_platform_fkey"
        FOREIGN KEY ("platform") REFERENCES "discovery_rail_platform_policies"("platform")
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "discovery_rail_policy_entries_rail_key_fkey"
        FOREIGN KEY ("rail_key") REFERENCES "discovery_rail_catalog"("key")
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE UNIQUE INDEX "discovery_rail_policy_entries_fixed_position_key"
    ON "discovery_rail_policy_entries"("platform", "position")
    WHERE "enabled" = true AND "rotation_pool" IS NULL;

CREATE INDEX "discovery_rail_policy_entries_platform_enabled_position_idx"
    ON "discovery_rail_policy_entries"("platform", "enabled", "position");

CREATE INDEX "discovery_rail_policy_entries_platform_rotation_pool_enabled_idx"
    ON "discovery_rail_policy_entries"("platform", "rotation_pool", "enabled");

CREATE INDEX "discovery_rail_policy_entries_rail_key_idx"
    ON "discovery_rail_policy_entries"("rail_key");

INSERT INTO "discovery_rail_catalog" (
    "key", "label", "content_kind", "requires_auth", "supported_platforms", "catalog_version"
)
VALUES
    ('followed_comedian_shows', 'Shows from followed comedians', 'show', true, '["web", "ios", "android"]'::jsonb, 1),
    ('trending_comedians', 'Trending comedians', 'comedian', false, '["web", "ios", "android"]'::jsonb, 1),
    ('shows_tonight', 'Shows tonight', 'show', false, '["web", "ios", "android"]'::jsonb, 1),
    ('nearby_shows', 'Nearby shows', 'show', false, '["web"]'::jsonb, 1),
    ('trending_this_week', 'Trending this week', 'show', false, '["web", "ios", "android"]'::jsonb, 1),
    ('popular_clubs', 'Popular clubs', 'club', false, '["web", "ios", "android"]'::jsonb, 1),
    ('trending_podcasts', 'Trending podcasts', 'podcast', false, '["ios", "android"]'::jsonb, 1)
ON CONFLICT ("key") DO NOTHING;

INSERT INTO "discovery_rail_platform_policies" (
    "platform", "policy_version", "catalog_version", "cycle_cadence_hours"
)
VALUES
    ('web', 1, 1, 24),
    ('ios', 1, 1, 24),
    ('android', 1, 1, 24)
ON CONFLICT ("platform") DO NOTHING;

INSERT INTO "discovery_rail_policy_entries" (
    "platform", "rail_key", "enabled", "position", "rotation_pool", "weight"
)
VALUES
    ('web', 'followed_comedian_shows', true, 0, NULL, 1),
    ('web', 'trending_comedians', true, 1, NULL, 1),
    ('web', 'shows_tonight', true, 2, NULL, 1),
    ('web', 'nearby_shows', true, 3, NULL, 1),
    ('web', 'trending_this_week', true, 4, NULL, 1),
    ('web', 'popular_clubs', true, 5, NULL, 1),
    ('ios', 'shows_tonight', true, 0, NULL, 1),
    ('ios', 'followed_comedian_shows', true, 1, NULL, 1),
    ('ios', 'trending_this_week', true, 2, NULL, 1),
    ('ios', 'trending_comedians', true, 3, NULL, 1),
    ('ios', 'popular_clubs', true, 4, NULL, 1),
    ('ios', 'trending_podcasts', true, 5, NULL, 1),
    ('android', 'shows_tonight', true, 0, NULL, 1),
    ('android', 'trending_this_week', true, 1, NULL, 1),
    ('android', 'followed_comedian_shows', true, 2, NULL, 1),
    ('android', 'trending_comedians', true, 3, NULL, 1),
    ('android', 'popular_clubs', true, 4, NULL, 1),
    ('android', 'trending_podcasts', true, 5, NULL, 1)
ON CONFLICT ("platform", "rail_key") DO NOTHING;
