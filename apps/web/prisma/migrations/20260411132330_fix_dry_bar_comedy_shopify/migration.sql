-- Fix Dry Bar Comedy (club 497) — venue moved from SeatEngine to Shopify;
-- update scraper type, scraping_url, clear stale seatengine_id, fill location.
-- Also hide and rename duplicate club 635 (same venue, no website configured).

-- Rename and hide duplicate club 635 first (frees up the name for club 497)
UPDATE "clubs"
SET name = 'Dry Bar Comedy [Duplicate]', visible = false
WHERE id = 635;

-- Update club 497: switch to Shopify scraper, rename, and fill location data
UPDATE "clubs"
SET
    scraper       = 'shopify',
    scraping_url  = 'https://store.drybarcomedy.com/collections/tickets',
    seatengine_id = NULL,
    name          = 'Dry Bar Comedy',
    city          = 'Provo',
    state         = 'UT',
    zip_code      = '84601',
    address       = '295 W Center St',
    timezone      = 'America/Denver',
    website       = 'https://store.drybarcomedy.com'
WHERE id = 497;
