-- TASK-3206: Onboard Improv Impact (Roseville, CA) via generic Squarespace.
--
-- Improv Impact is a dedicated improv-comedy theater in Roseville, CA. Its own
-- Squarespace site (theimprovimpact.com) publishes its show calendar via the
-- Events collection "Calendar" (collectionId 55930ffae4b0c0b24dfc2fe8) exposed
-- at /api/open/GetItemsByMonth.
--
-- The calendar is MIXED-USE: it lists the public, ticketed monthly comedy
-- showcase ("You Shoulda Been There!" / "PLACEHOLDER Show" — first Saturday of
-- every month, "$10 at the door", high-energy improv comedy) alongside
-- non-public class/practice sessions ("Improv Playground" — a beginner improv
-- CLASS; "Longform Improv Jam" — a practice JAM). We onboard with
-- exclude_title_patterns so only the public comedy shows are persisted; the
-- class/jam rows are dropped before emit.

INSERT INTO clubs (
    name,
    address,
    website,
    zip_code,
    timezone,
    visible,
    city,
    state,
    status,
    club_type,
    google_place_id
)
SELECT
    'Improv Impact',
    '401-B Vernon St',
    'https://www.theimprovimpact.com/',
    '95678',
    'America/Los_Angeles',
    TRUE,
    'Roseville',
    'CA',
    'active',
    'club',
    'ChIJ44DlxaIhm4ARmgJA-sY9PKo'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJ44DlxaIhm4ARmgJA-sY9PKo'
        OR lower(name) = lower('Improv Impact')
);

UPDATE clubs
   SET address = '401-B Vernon St',
       website = 'https://www.theimprovimpact.com/',
       zip_code = '95678',
       timezone = 'America/Los_Angeles',
       visible = TRUE,
       city = 'Roseville',
       state = 'CA',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJ44DlxaIhm4ARmgJA-sY9PKo')
 WHERE google_place_id = 'ChIJ44DlxaIhm4ARmgJA-sY9PKo'
    OR lower(name) = lower('Improv Impact');

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata
)
SELECT
    c.id,
    'squarespace'::"ScrapingPlatform",
    'squarespace',
    'https://www.theimprovimpact.com/api/open/GetItemsByMonth?collectionId=55930ffae4b0c0b24dfc2fe8',
    0,
    TRUE,
    jsonb_build_object(
        'exclude_title_patterns', jsonb_build_array(
            'Improv Playground',
            'Longform Improv Jam'
        )
    )
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJ44DlxaIhm4ARmgJA-sY9PKo'
        OR lower(c.name) = lower('Improv Impact'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'squarespace'::"ScrapingPlatform"
          AND s.priority = 0
   );

UPDATE scraping_sources s
   SET scraper_key = 'squarespace',
       source_url = 'https://www.theimprovimpact.com/api/open/GetItemsByMonth?collectionId=55930ffae4b0c0b24dfc2fe8',
       enabled = TRUE,
       metadata = jsonb_build_object(
           'exclude_title_patterns', jsonb_build_array(
               'Improv Playground',
               'Longform Improv Jam'
           )
       ),
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.platform = 'squarespace'::"ScrapingPlatform"
   AND s.priority = 0
   AND (c.google_place_id = 'ChIJ44DlxaIhm4ARmgJA-sY9PKo'
        OR lower(c.name) = lower('Improv Impact'));
