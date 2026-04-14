-- Hide The Conway Muse (club 811)
-- Venue rebranded to Arcadian Public House (conwaymuse.com 301-redirects to arcadianpublichouse.com);
-- SeatEngine venue 240 returns generic homepage (dead);
-- venue is a live music venue, not a comedy club — zero comedy shows listed;
-- now uses GoDaddy Website Builder with built-in booking
UPDATE "clubs"
SET visible = false
WHERE id = 811;
