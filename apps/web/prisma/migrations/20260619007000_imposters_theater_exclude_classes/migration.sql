-- Filter class sessions out of Imposters Theater's Squarespace scrape — TASK-2888
--
-- Imposters Theater (club#8719, onboarded in 20260616105700) runs on the generic
-- `squarespace` scraper, but its single events collection mixes public comedy
-- shows with improv-school class sessions / workshops / camps (~1/3 of items).
-- The squarespace scraper now supports an opt-in title filter via
-- scraping_sources.metadata.exclude_title_patterns (a list of case-insensitive
-- regexes; absent = keep everything, so other Squarespace venues are unaffected).
--
-- This sets the conservative class-exclusion patterns for Imposters. On a fresh
-- DB the venue's first scrape is filtered from the start; in prod the 45
-- already-ingested class rows were purged out-of-band.
--
-- Idempotent: the jsonb merge re-applies the same value on re-run.

UPDATE scraping_sources
SET metadata = metadata || '{"exclude_title_patterns": ["\\bLevel \\d", "Workshop", "\\bCamp\\b", "Try Improv", "Try Standup", "Bootcamp", "Intro to", "Rec League", "Registration", "Grad Night", "Grad Showcase", "\\(Table Read\\)", "\\bBasics\\b", "Private Event"]}'::jsonb
WHERE scraper_key = 'squarespace'
  AND club_id = (SELECT id FROM clubs WHERE name = 'Imposters Theater');
