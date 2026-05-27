-- Google Places provenance on clubs: the resolved place_id (text-searched by
-- name + city/state) and the photo's required author attributions (JSON),
-- populated when a club image is sourced from Google Places rather than the
-- club website. Both nullable; backfilled lazily by the source_club_images job.
ALTER TABLE "clubs" ADD COLUMN "google_place_id" TEXT;
ALTER TABLE "clubs" ADD COLUMN "google_place_attribution" JSONB;
