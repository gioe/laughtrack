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
    website TEXT unique,
    is_pseudonym boolean DEFAULT false,
    popularity_score double precision DEFAULT '0'::double precision,
    non_comedian boolean DEFAULT false
);