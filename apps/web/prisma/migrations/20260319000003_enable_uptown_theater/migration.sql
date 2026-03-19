-- Re-enable Uptown Theater (id=80) with the new uptown_theater scraper.
-- The club was disabled in TASK-420 because the json_ld scraper returned zero shows
-- (the listing page only has CollectionPage JSON-LD with event URLs, not ComedyEvent objects).
-- A dedicated scraper (key='uptown_theater') was built in TASK-448 that:
--   1. Fetches the events listing page and extracts event URLs from CollectionPage JSON-LD
--   2. Fetches each event detail page and extracts ComedyEvent JSON-LD
--   3. Transforms via JsonLdTransformer

UPDATE clubs SET visible = true, scraper = 'uptown_theater' WHERE id = 80;
