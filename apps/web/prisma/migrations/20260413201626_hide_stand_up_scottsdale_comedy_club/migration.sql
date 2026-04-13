-- Hide Stand Up Scottsdale Comedy Club (club 216)
-- Permanently closed; Yelp marks "CLOSED"; ABC15 reported closure;
-- website (standupscottsdale.com) hijacked by spam storefront;
-- SeatEngine API returns 404 for venue 13 (v1 and default);
-- 0 total shows
UPDATE "clubs" SET "visible" = false WHERE "id" = 216;
