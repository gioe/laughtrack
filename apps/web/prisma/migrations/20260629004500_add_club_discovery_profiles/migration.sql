CREATE TABLE club_discovery_profiles (
    club_id INTEGER PRIMARY KEY REFERENCES clubs(id) ON DELETE CASCADE,
    primary_show_type TEXT,
    show_type_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    comedy_show_count INTEGER NOT NULL DEFAULT 0,
    non_comedy_show_count INTEGER NOT NULL DEFAULT 0,
    mixed_programming BOOLEAN NOT NULL DEFAULT false,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT club_discovery_profiles_comedy_show_count_nonnegative
        CHECK (comedy_show_count >= 0),
    CONSTRAINT club_discovery_profiles_non_comedy_show_count_nonnegative
        CHECK (non_comedy_show_count >= 0),
    CONSTRAINT club_discovery_profiles_confidence_range
        CHECK (confidence >= 0 AND confidence <= 1)
);

CREATE INDEX club_discovery_profiles_primary_show_type_idx
    ON club_discovery_profiles(primary_show_type);

CREATE INDEX club_discovery_profiles_mixed_programming_idx
    ON club_discovery_profiles(mixed_programming);
