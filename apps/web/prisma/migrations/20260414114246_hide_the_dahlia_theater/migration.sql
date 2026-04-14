-- Hide The Dahlia Theater (club 346)
-- Venue rebranded to "Canby Pioneer Chapel Performing Arts" under new ownership (2021);
-- thedahliatheater.com is dead (ECONNREFUSED); SeatEngine venue 144 returns 404;
-- SeatEngine subdomain redirects to generic seatengine.com; venue is now a music/wedding
-- venue, not a comedy club; 0 total shows ever scraped.
UPDATE "clubs"
SET "visible" = false
WHERE "id" = 346;
