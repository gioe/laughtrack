-- TASK-3592: resolve the remaining needs_manual_research dedicated-club
-- candidates from the TASK-3588 ComedyTickets set.
--
-- ComedyTickets is used only as a discovery signal; it is never a scrape
-- target. Each row below was verified against the venue's OWN first-party
-- website and smoke-tested end-to-end with the real scraper HTTP stack
-- (future-show counts as of 2026-07-06):
--   * Loony Bin Little Rock : standup_media  (119 future shows)
--   * Loony Bin Tulsa       : standup_media  (141 future shows)
--   * Loony Bin Wichita     : standup_media  (105 future shows)
--   * Dallas Comedy Club    : json_ld/Prekindle (535 future shows)
--   * Hyena's Albuquerque   : json_ld/Prekindle (103 future shows)
--   * Big Laugh Fort Worth  : json_ld (SeatEngine whitelabel page) (61 future shows)
--   * Lafayette Comedy      : json_ld (3 future shows)
--   * Howler Comedy Club    : wix_events (15 future shows)
--   * Laughs Comedy Club    : the_events_calendar / Tribe (37 future shows)
--
-- High Line Comedy Club was created concurrently by another session with a
-- broken eventbrite source (org 242807453 -> 0 shows). The trailing UPDATE
-- corrects it to the verified organizer (org 91898788783 -> 21 future shows).
--
-- Duplicate guard: do not insert a club when either the canonical name already
-- exists or another row has the same normalized street-number/street-name key.
-- Source guard: only insert a scraping_sources row when the club has no other
-- enabled source.

WITH candidates AS (
    SELECT *
    FROM (
        VALUES
            (
                'Loony Bin Comedy Club - Little Rock',
                '10301 N Rodney Parham Rd, Little Rock, AR 72227',
                'https://lr.loonybincomedy.com',
                '72227', '', 'America/Chicago', 'Little Rock', 'AR',
                'custom', 'standup_media', 'https://lr.loonybincomedy.com/events',
                NULL::text,
                '{"standup_media_location_id":"46a4734a-d472-4d42-9712-3574fd06ed97","standup_media_dbname":"looneybin_prod"}'::jsonb
            ),
            (
                'Loony Bin Comedy Club - Tulsa',
                '6808 S Memorial Dr Ste 234, Tulsa, OK 74133',
                'https://tulsa.loonybincomedy.com',
                '74133', '', 'America/Chicago', 'Tulsa', 'OK',
                'custom', 'standup_media', 'https://tulsa.loonybincomedy.com/events',
                NULL::text,
                '{"standup_media_location_id":"bca30415-8e4e-4ec5-817d-52222ac57427","standup_media_dbname":"looneybin_prod"}'::jsonb
            ),
            (
                'Loony Bin Comedy Club - Wichita',
                '8406 W Central Ave, Wichita, KS 67212',
                'https://wichita.loonybincomedy.com',
                '67212', '', 'America/Chicago', 'Wichita', 'KS',
                'custom', 'standup_media', 'https://wichita.loonybincomedy.com/events',
                NULL::text,
                '{"standup_media_location_id":"bb17db1f-8d39-434b-87b2-479fa2d2ffa3","standup_media_dbname":"Wichita_prod"}'::jsonb
            ),
            (
                'Dallas Comedy Club',
                '3036 Elm Street, Dallas, TX 75226',
                'https://dallas-comedyclub.com',
                '75226', '(214) 814-1980', 'America/Chicago', 'Dallas', 'TX',
                'custom', 'json_ld', 'https://www.prekindle.com/events/dallas-comedy-club',
                NULL::text, '{}'::jsonb
            ),
            (
                'Hyena''s Comedy Nightclub Albuquerque',
                '2100 Louisiana Blvd NE #434, Albuquerque, NM 87110',
                'https://www.hyenascomedynightclub.com/albuquerque',
                '87110', '(505) 216-6009', 'America/Denver', 'Albuquerque', 'NM',
                'custom', 'json_ld', 'https://www.prekindle.com/events/hyenas-albuquerque',
                NULL::text, '{}'::jsonb
            ),
            (
                'Big Laugh Comedy Club',
                '604 Main St Suite 100, Fort Worth, TX 76102',
                'https://fortworth.blcomedy.com',
                '76102', '', 'America/Chicago', 'Fort Worth', 'TX',
                'custom', 'json_ld', 'https://fortworth.blcomedy.com/calendar',
                NULL::text, '{}'::jsonb
            ),
            (
                'Lafayette Comedy',
                'Lafayette, LA 70506',
                'https://www.lafayettecomedy.com',
                '70506', '(337) 298-4373', 'America/Chicago', 'Lafayette', 'LA',
                'custom', 'json_ld', 'https://www.lafayettecomedy.com/calendar',
                NULL::text, '{}'::jsonb
            ),
            (
                'Howler Comedy Club',
                '151 N 8th St, Lincoln, NE 68508',
                'https://www.howlercomedy.com',
                '68508', '', 'America/Chicago', 'Lincoln', 'NE',
                'wix_events', 'wix_events', 'https://www.howlercomedy.com/upcoming-comedy-shows-lincoln-ne',
                NULL::text, '{}'::jsonb
            ),
            (
                'Laughs Comedy Club',
                '5220 Roosevelt Way NE, Seattle, WA 98105',
                'https://laughscomedyclub.com',
                '98105', '', 'America/Los_Angeles', 'Seattle', 'WA',
                'tribe_events', 'the_events_calendar', 'https://laughscomedyclub.com/wp-json/tribe/events/v1/events',
                NULL::text, '{}'::jsonb
            )
    ) AS v(
        name, address, website, zip_code, phone_number, timezone, city, state,
        platform, scraper_key, source_url, eventbrite_id, metadata
    )
),
normalized_candidates AS (
    SELECT
        c.*,
        lower(regexp_replace(split_part(c.address, ',', 1), '[^a-zA-Z0-9]+', '', 'g')) AS street_key
    FROM candidates c
),
inserted_clubs AS (
    INSERT INTO clubs (
        name, address, website, zip_code, phone_number, popularity,
        timezone, city, state, country, visible, status, club_type
    )
    SELECT
        nc.name, nc.address, nc.website, nc.zip_code, nc.phone_number, 0,
        nc.timezone, nc.city, nc.state, 'US', TRUE, 'active', 'club'
    FROM normalized_candidates nc
    WHERE NOT EXISTS (
        SELECT 1
        FROM clubs existing
        WHERE existing.name = nc.name
           OR lower(regexp_replace(split_part(existing.address, ',', 1), '[^a-zA-Z0-9]+', '', 'g')) = nc.street_key
    )
    ON CONFLICT (name) DO NOTHING
    RETURNING id, name
),
preexisting_target_clubs AS (
    SELECT existing.id AS club_id, nc.name
    FROM normalized_candidates nc
    JOIN clubs existing
      ON existing.name = nc.name
      OR lower(regexp_replace(split_part(existing.address, ',', 1), '[^a-zA-Z0-9]+', '', 'g')) = nc.street_key
),
target_clubs AS (
    SELECT
        COALESCE(ic.id, ptc.club_id) AS club_id,
        nc.platform, nc.scraper_key, nc.source_url, nc.eventbrite_id, nc.metadata
    FROM normalized_candidates nc
    LEFT JOIN inserted_clubs ic ON ic.name = nc.name
    LEFT JOIN preexisting_target_clubs ptc ON ptc.name = nc.name
    WHERE COALESCE(ic.id, ptc.club_id) IS NOT NULL
)
INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata
)
SELECT
    tc.club_id,
    tc.platform::"ScrapingPlatform",
    tc.scraper_key,
    tc.source_url,
    tc.eventbrite_id,
    0,
    TRUE,
    tc.metadata
FROM target_clubs tc
WHERE NOT EXISTS (
    SELECT 1
    FROM scraping_sources ss
    WHERE ss.club_id = tc.club_id
      AND ss.enabled = TRUE
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET
    scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    eventbrite_id = EXCLUDED.eventbrite_id,
    enabled = TRUE,
    metadata = EXCLUDED.metadata,
    updated_at = NOW()
WHERE scraping_sources.enabled = FALSE;

-- Correct the concurrently-created High Line Comedy Club eventbrite source.
-- A parallel session enabled org 242807453 (source_url https://www.eventbrite.com),
-- which returns 0 shows; the verified first-party organizer is 91898788783
-- (smoke-tested 2026-07-06 -> 21 future shows). Guarded to only rewrite the
-- broken value so re-runs are idempotent.
UPDATE scraping_sources ss
SET
    eventbrite_id = '91898788783',
    source_url = 'https://www.eventbrite.com/o/high-line-comedy-club-91898788783',
    updated_at = NOW()
FROM clubs c
WHERE ss.club_id = c.id
  AND c.name = 'High Line Comedy Club'
  AND ss.scraper_key = 'eventbrite'
  AND ss.enabled = TRUE
  AND ss.eventbrite_id IS DISTINCT FROM '91898788783';

