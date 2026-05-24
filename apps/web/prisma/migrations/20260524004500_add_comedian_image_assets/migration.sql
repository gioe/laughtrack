CREATE TABLE comedian_image_assets (
    id SERIAL PRIMARY KEY,
    comedian_id INTEGER NOT NULL REFERENCES comedians(id) ON DELETE CASCADE,
    source_image_url TEXT NOT NULL,
    original_path TEXT NOT NULL,
    avatar_path TEXT NOT NULL,
    hero_path TEXT NOT NULL,
    mime_type TEXT NULL,
    width INTEGER NULL,
    height INTEGER NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX comedian_image_assets_comedian_id_idx
    ON comedian_image_assets(comedian_id);

CREATE INDEX comedian_image_assets_is_active_idx
    ON comedian_image_assets(is_active);

CREATE UNIQUE INDEX comedian_image_assets_one_active_per_comedian_idx
    ON comedian_image_assets(comedian_id)
    WHERE is_active;
