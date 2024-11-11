/*
 Creates table comedians.
 */
CREATE TABLE IF NOT EXISTS comedians (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL unique,
    instagram_account TEXT,
    instagram_followers INTEGER,
    tiktok_account TEXT,
    tiktok_followers INTEGER,
    youtube_account TEXT,
    youtube_followers INTEGER,
    website TEXT,
    popularity_score double precision DEFAULT '0'::double precision,
    uuid text UNIQUE
);
