-- Add nullable latitude/longitude columns to clubs for in-app MapKit pins.
-- Backfilled by apps/scraper/scripts/core/backfill_club_coordinates.py.

ALTER TABLE "clubs"
    ADD COLUMN "latitude"  DOUBLE PRECISION,
    ADD COLUMN "longitude" DOUBLE PRECISION;
