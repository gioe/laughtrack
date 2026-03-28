-- TASK-742: Add The Comedy Clubhouse as a new venue
-- Website: https://www.thecomedyclubhouse.com
-- Located at 1462 N Ashland Ave, Chicago, IL 60622 (Wicker Park / Bucktown).
-- Stand-up, improv, and sketch comedy. Operated by One Group Mind improvisers' union.
-- Tickets sold via TicketSource at: https://www.ticketsource.com/thecomedyclubhouse

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'The Comedy Clubhouse',
    '1462 N Ashland Ave',
    'Chicago',
    'IL',
    '60622',
    'America/Chicago',
    'comedy_clubhouse',
    TRUE,
    'https://www.thecomedyclubhouse.com',
    'https://www.ticketsource.com/thecomedyclubhouse'
);
