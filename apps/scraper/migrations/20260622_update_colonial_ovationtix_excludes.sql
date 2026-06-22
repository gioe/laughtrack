-- TASK-3168: Add Colonial OvationTix exclusions after live verification.
--
-- The first live scrape showed the generic comedy keyword filter can keep a
-- silent-film-with-live-score production because its description mentions
-- physical comedy. Preserve the title allowlist for stand-up acts, and exclude
-- known film/music/dance series by title.

UPDATE scraping_sources s
   SET metadata = '{
       "comedy_filter": true,
       "comedy_title_allowlist": [
           "Patton Oswalt",
           "Margaret Cho",
           "Juston McKinney",
           "Frank Santos",
           "Nurse Blake"
       ],
       "exclude_title_patterns": [
           "^FILM:",
           "Philharmonic",
           "Ballet",
           "Dance Company"
       ]
   }'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND c.google_place_id = 'ChIJ453HtoBz4YkRCrrHlZU2Eq8'
   AND s.scraper_key = 'ovationtix'
   AND s.ovationtix_id = '36697';
