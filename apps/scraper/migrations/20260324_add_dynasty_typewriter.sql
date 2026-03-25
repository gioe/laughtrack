-- TASK-670: Add Dynasty Typewriter (Los Angeles, CA) as a new venue
-- Website: https://www.dynastytypewriter.com
-- Address: 2511 Wilshire Blvd, Los Angeles, CA 90057
-- Shows are fetched from the SquadUp API (user_id=7408591).
-- The scraping_url is the SquadUp API endpoint; a Referer header is added at runtime.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Dynasty Typewriter',
    '2511 Wilshire Blvd',
    'Los Angeles',
    'CA',
    '90057',
    'America/Los_Angeles',
    'dynasty_typewriter',
    TRUE,
    'https://www.dynastytypewriter.com',
    'https://www.squadup.com/api/v3/events?user_ids=7408591&page_size=100&topics_exclude=true&additional_attr=sold_out&include=custom_fields'
);
