/*
 Creates table Clubs.
 */
CREATE TABLE IF NOT EXISTS clubs (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL unique,
    city TEXT NOT NULL,
    address TEXT NOT NULL,
    latitude numeric(10, 6) NOT NULL,
    longitude numeric(10, 6) NOT NULL,
    base_url TEXT NOT NULL,
    schedule_page_url TEXT NOT NULL,
    timezone TEXT NOT NULL,
    scraping_config JSON NOT NULL,
    image_name TEXT
);