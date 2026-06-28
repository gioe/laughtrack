-- TASK-3484: TASK-3042 disabled per-venue ticketmaster_comedy sources covered
-- by ticketmaster_national, but UPSERT_CLUB_BY_TICKETMASTER_VENUE re-enabled
-- them on the next national pass. Re-apply the cutover after the upsert SQL fix
-- that preserves disabled ticketmaster_comedy rows on conflict.
--
-- Keep-list matches the TASK-3042 edge cases minus the four IDs disabled by
-- TASK-3043 once national learned to resolve existing venues by ticketmaster_id.

-- Ensure the batched national target is active.
UPDATE source_targets
   SET enabled = TRUE,
       status = 'active',
       updated_at = NOW()
 WHERE slug = 'ticketmaster-national';

UPDATE scraping_sources
   SET enabled = TRUE,
       updated_at = NOW()
 WHERE scraper_key = 'ticketmaster_national'
   AND source_target_id IS NOT NULL;

-- Disable every covered venue-specific Ticketmaster source. The disabled rows
-- remain useful identity anchors: ticketmaster_national resolves by
-- scraping_sources.ticketmaster_id before falling back to club name.
UPDATE scraping_sources
   SET enabled = FALSE,
       updated_at = NOW(),
       metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
           'task_3484_ticketmaster_national_cutover',
           jsonb_build_object(
               'disabled_at', NOW(),
               'reason', 'covered by ticketmaster_national; keep disabled to avoid nightly per-venue Ticketmaster fanout'
           )
       )
 WHERE scraper_key = 'ticketmaster_comedy'
   AND enabled = TRUE
   AND ticketmaster_id IS NOT NULL
   AND ticketmaster_id NOT IN (
        'KovZ917ASlK',
        'KovZ917AVf2',
        'KovZ917AYlh',
        'KovZ917Am4e',
        'KovZ917Atn3',
        'KovZpZA17ItA',
        'KovZpZA1EanA',
        'KovZpZA1IFeA',
        'KovZpZA6takA',
        'KovZpZAE7v6A',
        'KovZpZAEAAlA',
        'KovZpZAEe7IA',
        'KovZpZAF76IA',
        'KovZpZAF7dtA',
        'KovZpZAFAtlA',
        'KovZpZAJJEaA',
        'KovZpZAJtF6A',
        'KovZpZAaJ17A',
        'KovZpZAdIe1A',
        'KovZpa2MCe',
        'KovZpa61pe',
        'KovZpaK80e',
        'KovZpakiGe',
        'KovZpapY1e',
        'Z6r9jZAkFe',
        'Z6r9jZd1ee',
        'Z6r9jZk7Fe',
        'Z7r9jZa7D2',
        'Z7r9jZadaD',
        'Z7r9jZak1X',
        'ZFr9jZ71Fe',
        'ZFr9jZ7vAA',
        'Zkr9jZddeh'
   );
