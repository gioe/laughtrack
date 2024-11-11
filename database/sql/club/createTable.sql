/*
 Creates table clubs.
 */
CREATE TABLE clubs (
    id SERIAL PRIMARY KEY,
    name text NOT NULL UNIQUE,
    address text NOT NULL,
    website text NOT NULL,
    scraping_page_url text NOT NULL,
    popularity_score double precision DEFAULT '0' :: double precision,
    zip_code character varying(10),
    city_id integer REFERENCES cities(id) ON DELETE CASCADE
);