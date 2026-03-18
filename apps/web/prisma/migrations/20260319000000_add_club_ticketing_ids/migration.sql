-- Add ticketing platform ID columns to clubs table.
-- These columns store the venue ID on each ticketing platform and are
-- required by the per-venue scrapers (seatengine, eventbrite, ticketmaster).
ALTER TABLE "clubs"
    ADD COLUMN IF NOT EXISTS "seatengine_id" TEXT,
    ADD COLUMN IF NOT EXISTS "eventbrite_id" TEXT,
    ADD COLUMN IF NOT EXISTS "ticketmaster_id" TEXT;
