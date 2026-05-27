CREATE TABLE club_image_assets (
    id SERIAL PRIMARY KEY,
    club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    source_image_url TEXT NOT NULL,
    original_path TEXT NOT NULL,
    icon_path TEXT NULL,
    hero_path TEXT NULL,
    mime_type TEXT NULL,
    width INTEGER NULL,
    height INTEGER NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX club_image_assets_club_id_idx
    ON club_image_assets(club_id);

CREATE INDEX club_image_assets_is_active_idx
    ON club_image_assets(is_active);

CREATE UNIQUE INDEX club_image_assets_one_active_per_club_idx
    ON club_image_assets(club_id)
    WHERE is_active;
