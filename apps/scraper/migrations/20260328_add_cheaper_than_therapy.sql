-- TASK-746: Add Cheaper Than Therapy as a new venue
-- Website: https://cttcomedy.com
-- Located at 533 Sutter St, San Francisco, CA 94102 (Shelton Theater).
-- San Francisco comedy club running Wed–Sun, 7:45 PM nightly; Fri–Sat also 9:45 PM.
-- Primary ticketing is via Ninkashi (tickets.cttcomedy.com), but the venue also
-- maintains an active Eventbrite organizer account with all upcoming shows.
-- Organizer: "Cheaper Than Therapy Comedy" (organizer ID: 7381983683)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'Cheaper Than Therapy',
    '533 Sutter St',
    'San Francisco',
    'CA',
    '94102',
    'America/Los_Angeles',
    '7381983683',
    'eventbrite',
    TRUE,
    'https://cttcomedy.com',
    'https://www.eventbrite.com/o/cheaper-than-therapy-7381983683'
);
