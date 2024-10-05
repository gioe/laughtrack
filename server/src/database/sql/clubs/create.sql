CREATE TABLE IF NOT EXISTS clubs (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL unique,
    city TEXT NOT NULL,
    address TEXT NOT NULL,
    base_url TEXT NOT NULL,
    schedule_page_url TEXT NOT NULL,
    timezone TEXT NOT NULL,
    scraping_config JSON NOT NULL,
    popularity_score double precision DEFAULT '0'::double precision,
    zip_code VARCHAR(10)
);