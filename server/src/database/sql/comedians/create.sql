/*
 Creates table Comedians.
 */
CREATE TABLE IF NOT EXISTS comedians (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL unique,
    instagram_account TEXT unique,
    instagram_followers INTEGER,
    tiktok_account TEXT unique,
    tiktok_followers INTEGER,
    youtube_account TEXT unique,
    youtube_followers INTEGER,
    website TEXT unique,
    popularity_score double precision DEFAULT '0'::double precision
);