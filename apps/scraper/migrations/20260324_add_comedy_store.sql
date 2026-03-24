-- TASK-664: Add The Comedy Store as a new venue
-- Website: https://thecomedystore.com/
-- The Comedy Store is the iconic West Hollywood comedy club at 8433 W Sunset Blvd,
-- founded in 1972.  Shows are listed on a day-by-day calendar powered by the venue's
-- own CMS; tickets are sold through ShowClix (venue ID 30111).
-- The scraper fetches /calendar/YYYY-MM-DD for each upcoming day.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'The Comedy Store',
    '8433 W Sunset Blvd',
    'West Hollywood',
    'CA',
    '90069',
    'America/Los_Angeles',
    'comedy_store',
    TRUE,
    'https://thecomedystore.com',
    'https://thecomedystore.com/calendar'
);
