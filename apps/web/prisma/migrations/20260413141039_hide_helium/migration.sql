-- Restore Helium (club 1136) — this is Lake Theater & Cafe (Lake Oswego, OR), not a Helium duplicate
-- Originally hidden in error; the SeatEngine subdomain is branded "Helium" but the venue is independent
UPDATE "clubs" SET "visible" = true WHERE "id" = 1136;
