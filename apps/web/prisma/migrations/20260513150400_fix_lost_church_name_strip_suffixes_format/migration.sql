-- TASK-2168 review fix: rewrite Lost Church's name_strip_suffixes as a JSON array.
--
-- The prior fold migration (20260513150100) stored the suffix list as a CSV
-- string ' - San Francisco, - SF, - sf'. The scraper's _coerce_string_list
-- splits CSV chunks on ',' and strips whitespace per chunk for venue-ID-style
-- inputs (where surrounding whitespace is formatting), which silently eats the
-- meaningful leading space on each suffix and yields ['- San Francisco',
-- '- SF', '- sf'] — one char short of the prior LostChurchEvent constants.
-- Show.__post_init__ trims trailing whitespace so the final stored name is
-- correct, but the parser is misbehaving and the next PatronTicket venue that
-- relies on a more complex (mid-string) suffix could regress in a way
-- post_init can't paper over.
--
-- Storing the suffixes as a JSON array preserves each entry verbatim through
-- _coerce_string_list's list-branch (which no longer strips per-entry), so
-- the suffix matched against the upstream event name has its leading space
-- intact.
UPDATE scraping_sources
SET
    metadata = COALESCE(metadata, '{}'::jsonb)
        || jsonb_build_object(
            'patronticket_name_strip_suffixes',
            jsonb_build_array(' - San Francisco', ' - SF', ' - sf')
        ),
    updated_at = NOW()
WHERE club_id = 1047
  AND scraper_key = 'patron_ticket';
