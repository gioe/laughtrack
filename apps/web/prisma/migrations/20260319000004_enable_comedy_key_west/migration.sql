-- Re-enable Comedy Key West (id=98) with the Punchup/Tixologi scraper.
--
-- The club was disabled in 20260319000002_disable_csr_clubs because the json_ld
-- scraper returns zero shows (the site is client-side rendered via Punchup/Next.js).
-- A dedicated scraper (key='comedy_key_west') was built in TASK-447 that parses the
-- venuePageCarousel RSC hydration data embedded in the Punchup streaming script tags.

UPDATE "Club"
SET
    visible = true,
    scraper = 'comedy_key_west',
    scraping_url = 'www.comedykeywest.com/shows'
WHERE id = 98;
