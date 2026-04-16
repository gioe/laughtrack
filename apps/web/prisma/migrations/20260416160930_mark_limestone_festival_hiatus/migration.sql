-- Mark Limestone Comedy Festival (club 834) as on hiatus for 2026.
-- The festival is a legitimate annual multi-venue comedy event in Bloomington, IN
-- (Year 12 ran May 29-31, 2025), but limestonefest.com homepage states
-- "Taking 2026 off. See ya when we see ya." — no 2026 edition planned.
-- Also upgrades website URL from http:// to https:// (site is live on HTTPS).
UPDATE clubs
SET status = 'hiatus',
    website = 'https://www.limestonefest.com',
    scraping_url = 'https://www.limestonefest.com'
WHERE id = 834;
