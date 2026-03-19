-- Disable Comedy Key West (id=98) and Uptown Theater (id=80)
-- Both clubs were temporarily assigned scraper='json_ld' during TASK-407 to suppress
-- "does not have a seatengine_id configured" errors, but they are client-side rendered
-- and do not emit JSON-LD at request time — the json_ld scraper returns zero shows.
--
-- Comedy Key West (id=98): uses Tixologi ticketing platform (CSR, no server-side JSON-LD)
-- Uptown Theater (id=80): custom Next.js site (CSR, no server-side JSON-LD)
--
-- Both are set visible=false until a proper scraper is built for each platform.

UPDATE "Club" SET visible = false, scraper = NULL WHERE id = 98;
UPDATE "Club" SET visible = false, scraper = NULL WHERE id = 80;
