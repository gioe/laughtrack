-- TASK-741: Add Logan Square Improv as a new venue
-- Website: https://logansquareimprov.com
-- Located at 2825 W. Diversey Ave, Chicago, IL 60647 (Logan Square neighborhood).
-- Non-profit improv theater with $5 shows Wednesday through Sunday; BYOB.
-- The venue events page embeds a Crowdwork/Fourthwall Tickets widget that calls:
--   https://crowdwork.com/api/v2/lsi/shows
-- (theatre slug "lsi" visible in Crowdwork network requests from logansquareimprov.com/events/)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Logan Square Improv',
    '2825 W Diversey Ave',
    'Chicago',
    'IL',
    '60647',
    'America/Chicago',
    'logan_square_improv',
    TRUE,
    'https://logansquareimprov.com',
    'https://crowdwork.com/api/v2/lsi/shows'
);
