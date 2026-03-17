-- Add total_shows column to clubs table
ALTER TABLE "clubs" ADD COLUMN "total_shows" INTEGER NOT NULL DEFAULT 0;

-- Backfill: count Show rows per club
UPDATE "clubs"
SET "total_shows" = (
    SELECT COUNT(*)
    FROM "shows"
    WHERE "shows"."club_id" = "clubs"."id"
);
