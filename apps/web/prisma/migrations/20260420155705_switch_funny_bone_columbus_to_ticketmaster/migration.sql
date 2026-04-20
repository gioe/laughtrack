-- Switch Funny Bone Columbus (id 308) from Etix (DataDome-blocked) to Ticketmaster (live_nation).
-- Etix blanket-blocks the scraper behind DataDome CAPTCHA (TASK-1647). The venue publishes
-- the same 20+ upcoming shows on Ticketmaster under venue id Z7r9jZadLM, which returns
-- structured event data without bot protection.
-- Also enriches previously-missing address/city/state/zip/country from the Ticketmaster
-- venue record.
UPDATE clubs
SET scraper = 'live_nation',
    ticketmaster_id = 'Z7r9jZadLM',
    address = '145 Easton Town Center',
    city = 'Columbus',
    state = 'OH',
    zip_code = '43219',
    country = 'US'
WHERE id = 308;
