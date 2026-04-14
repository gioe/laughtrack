-- Hide The Dope Show (club 529)
-- Not a venue — touring comedy showcase by Tyler Smith that performs at other clubs
-- (Tacoma Comedy Club, Spokane Comedy Club, New York Comedy Club, etc.);
-- SeatEngine venue 505 returns 404; 0 total shows ever scraped.
UPDATE "clubs"
SET "visible" = false
WHERE "id" = 529;
