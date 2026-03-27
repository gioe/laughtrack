-- TASK-736: Add The Annoyance Theatre & Bar Chicago as a new venue
-- Website: https://www.theannoyance.com
-- Located at 851 W. Belmont Ave, Chicago, IL 60657 (Lakeview).
-- Over 35 years of original comedy — improv, sketch, musical, and solo shows.
-- Ticketing platform: ThunderTix (theannoyance.thundertix.com)
-- Calendar API: https://theannoyance.thundertix.com/reports/calendar

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'The Annoyance Theatre',
    '851 W. Belmont Ave',
    'Chicago',
    'IL',
    '60657',
    'America/Chicago',
    'annoyance',
    TRUE,
    'https://www.theannoyance.com',
    'https://theannoyance.thundertix.com/reports/calendar'
);
