-- Per-organizer Eventbrite venue history (TASK-2859).
-- The scraper records, after each clean organizer-mode run, the distinct venue
-- club_ids a production company's /o/ feed produced shows for. A later clean run
-- diffs its current venue set against this persisted set to detect venues that
-- dropped entirely from the feed and reconcile their now-stale future shows.
-- Kept separate from production_company_venues so it never perturbs the lookup
-- that decides whether to build a synthetic organizer proxy.

CREATE TABLE "eventbrite_organizer_venues" (
    "production_company_id" INTEGER NOT NULL,
    "club_id" INTEGER NOT NULL,
    "last_seen_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT "eventbrite_organizer_venues_pkey" PRIMARY KEY ("production_company_id", "club_id"),
    CONSTRAINT "eventbrite_organizer_venues_production_company_id_fkey"
        FOREIGN KEY ("production_company_id") REFERENCES "production_companies"("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "eventbrite_organizer_venues_club_id_fkey"
        FOREIGN KEY ("club_id") REFERENCES "clubs"("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- Supports the cross-organizer safety check: "is this club_id covered by any
-- OTHER organizer's history?" (club_id lookup independent of production_company_id).
CREATE INDEX "eventbrite_organizer_venues_club_id_idx"
    ON "eventbrite_organizer_venues"("club_id");
