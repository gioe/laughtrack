-- TASK-735: Add iO Theater Chicago as a new venue
-- Website: https://ioimprov.com
-- Located at 1501 N Kingsbury St, Chicago, IL 60642 (River North).
-- Long-form improv since 1981; four stages with shows seven nights a week.
-- The venue homepage embeds a Crowdwork/Fourthwall Tickets widget that calls:
--   https://crowdwork.com/api/v2/iotheater/shows
-- (theatre slug "iotheater" visible on crowdwork.com/v/iotheater/shows)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'iO Theater',
    '1501 N Kingsbury St',
    'Chicago',
    'IL',
    '60642',
    'America/Chicago',
    'io_theater',
    TRUE,
    'https://ioimprov.com',
    'https://crowdwork.com/api/v2/iotheater/shows'
);
