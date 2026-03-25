-- TASK-691: Add Esther's Follies as a new venue
-- Website: https://www.esthersfollies.com/
-- Austin comedy institution since 1977 — sketch comedy, political satire, magic.
-- Location: 525 E. 6th Street, Austin, TX 78701
-- Shows: Thursday–Saturday nights (7 PM and 9 PM on Fri/Sat)
-- Ticketing: VBO Tickets (plugin.vbotickets.com, SiteID=5D695E7C-1246-4F54-BF57-B1D92D1E6B83, EID=39242)
-- Session is acquired from loadplugin; date slider returns ~6 weeks of upcoming shows.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Esther''s Follies',
    '525 E. 6th Street',
    'Austin',
    'TX',
    '78701',
    'America/Chicago',
    'esthers_follies',
    TRUE,
    'https://www.esthersfollies.com',
    'https://www.esthersfollies.com/tickets'
);
