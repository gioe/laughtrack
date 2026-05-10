-- TASK-2108: restore full Eventbrite organizer-mode coverage for venues whose
-- original TASK-1918 club rows remain hidden.
--
-- The enabled scraping_sources.eventbrite_id unique index prevents storing the
-- same organizer id on every per-venue destination club. Model each organizer
-- as a no-mapping production company instead: ScrapingService synthesizes an
-- in-memory Eventbrite organizer proxy from production_companies.scraping_url,
-- EventbriteScraper organizer mode groups by event venue, and
-- ClubHandler.upsert_for_eventbrite_venue routes shows to the visible per-venue
-- clubs without re-enabling the original hidden rows.

UPDATE clubs
SET visible = FALSE
WHERE id IN (199, 647, 1052);

INSERT INTO production_companies (
    name,
    slug,
    website,
    scraping_url,
    visible,
    show_name_keywords
)
VALUES
    (
        'The Riot Comedy Club',
        'the-riot-comedy-club-eventbrite-organizer',
        'https://www.theriothtx.com',
        'https://www.eventbrite.com/o/the-riot-comedy-club-29979960920',
        TRUE,
        ARRAY[]::text[]
    ),
    (
        'Backdoor Comedy Club',
        'backdoor-comedy-club-eventbrite-organizer',
        'https://www.backdoorcomedy.com',
        'https://www.eventbrite.com/o/backdoor-comedy-club-86805735233',
        TRUE,
        ARRAY[]::text[]
    ),
    (
        'Comedy At The Comet',
        'comedy-at-the-comet-eventbrite-organizer',
        'https://www.bombsawaycomedy.com',
        'https://www.eventbrite.com/o/bombs-away-comedy-18372505544',
        TRUE,
        ARRAY[]::text[]
    )
ON CONFLICT (slug) DO UPDATE
SET name = EXCLUDED.name,
    website = EXCLUDED.website,
    scraping_url = EXCLUDED.scraping_url,
    visible = TRUE,
    show_name_keywords = EXCLUDED.show_name_keywords;

-- These organizer rows must have no production_company_venues mappings. A
-- mapped production company uses the first mapped venue as a proxy, which would
-- retain that venue's single-venue eventbrite_id and defeat organizer mode.
DELETE FROM production_company_venues AS pcv
USING production_companies AS pc
WHERE pc.id = pcv.production_company_id
  AND pc.slug IN (
      'the-riot-comedy-club-eventbrite-organizer',
      'backdoor-comedy-club-eventbrite-organizer',
      'comedy-at-the-comet-eventbrite-organizer'
  );
