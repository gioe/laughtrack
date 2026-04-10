-- Hide BJ's Mobile Drive-In Theater (club 413)
-- SeatEngine page is dead (302 redirect to seatengine.com homepage).
-- No web presence as a comedy venue. Not a real comedy club.
UPDATE "clubs" SET "visible" = false WHERE "id" = 413;
