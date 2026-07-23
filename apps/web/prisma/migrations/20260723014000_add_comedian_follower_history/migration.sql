CREATE TYPE "SocialPlatform" AS ENUM ('instagram', 'tiktok', 'youtube');

CREATE TABLE comedian_follower_observations (
    id BIGSERIAL PRIMARY KEY,
    comedian_id INTEGER NOT NULL,
    platform "SocialPlatform" NOT NULL,
    follower_count INTEGER NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT comedian_follower_observations_follower_count_check
        CHECK (follower_count >= 0),
    CONSTRAINT comedian_follower_observations_comedian_id_fkey
        FOREIGN KEY (comedian_id) REFERENCES comedians(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT comedian_follower_observation_identity_key
        UNIQUE (comedian_id, platform, observed_at)
);

CREATE INDEX comedian_follower_observations_platform_observed_at_idx
    ON comedian_follower_observations(platform, observed_at);
