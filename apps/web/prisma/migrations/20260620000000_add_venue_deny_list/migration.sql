-- Add the venue_deny_list table — TASK-2895.
--
-- Records discovered venues (via discover-comedy-venues) that were evaluated
-- and rejected as non-comedy (e.g. live-music venues whose own calendar carries
-- no stand-up). Keyed on Google place_id so discover-nearby can classify them
-- "denied" and never re-file an onboarding task, and so a zero-show triage /
-- adopt-scraper pass recognises the venue as deliberately excluded, not a gap.
-- Mirrors the comedian_deny_list / podcast_deny_list pattern.
--
-- IF NOT EXISTS makes this a no-op on environments that already have the table.

CREATE TABLE IF NOT EXISTS "venue_deny_list" (
    "google_place_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "reason" TEXT NOT NULL DEFAULT '',
    "added_by" TEXT NOT NULL DEFAULT 'discovery_triage',
    "denied_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "venue_deny_list_pkey" PRIMARY KEY ("google_place_id")
);
