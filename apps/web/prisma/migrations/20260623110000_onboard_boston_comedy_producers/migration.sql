-- Onboard three active Boston-area roving comedy producers as Eventbrite
-- organizer-mode production_companies - TASK-3156 (follow-up from TASK-3151).
--
-- Glovebox Comedy Club and The Point Boston were filed as high-tier venues, but
-- neither is a fixed venue with its own scrapable comedy datasource:
--   - Glovebox (Hennessy's, 25 Union St): no own website (Linktree -> Eventbrite);
--     the producer that ran it (13th Road) has moved its current shows off
--     Hennessy's to Castle Island Brewing / Pub On Park, and the "Glovebox Comedy
--     Club" Eventbrite org (95938208163) is dormant ("Nothing planned right now").
--   - The Point (147 Hanover St): its own site (thepointboston.com) lists only
--     DJ/bingo nights, zero comedy/ticketing; comedy is run entirely by outside
--     promoters (Comedy Party -> Democracy Brewing; Like 2 Laugh -> Kushala Chelsea).
--
-- Resolution: producer, not venue. Each active producer is modeled as a
-- no-mapping Eventbrite organizer-mode production company (the TASK-2108 pattern):
-- ScrapingService synthesizes an in-memory organizer proxy from
-- production_companies.scraping_url, EventbriteScraper organizer mode groups by
-- event venue, and ClubHandler.upsert_for_eventbrite_venue routes each show to the
-- correct auto-created per-venue club (Castle Island Brewing, Democracy Brewing,
-- Kushala, etc.) -- those per-venue clubs are the browsable surfaces.
--
-- visible=TRUE here means SCRAPE-ENABLED: ProductionCompanyHandler
-- .get_all_production_companies() only loads visible production companies, so an
-- organizer-mode producer must be visible=TRUE to be scraped at all (matching the
-- working TASK-2108 rows Riot/Backdoor/Comet; the visible=FALSE rows like Milwaukee
-- Comedy / Whale City are intentionally disabled). Verified 2026-06-23: a real
-- organizer scrape returned 3 (13th Road), 2 (Comedy Party), 6 (Like 2 Laugh) shows.

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
        '13th Road',
        '13th-road-eventbrite-organizer',
        NULL,
        'https://www.eventbrite.com/o/13th-road-80836269443',
        TRUE,
        ARRAY[]::text[]
    ),
    (
        'Comedy Party',
        'comedy-party-eventbrite-organizer',
        'https://comedy-party.com',
        'https://www.eventbrite.com/o/comedy-party-16050866037',
        TRUE,
        ARRAY[]::text[]
    ),
    (
        'Like 2 Laugh Productions',
        'like-2-laugh-productions-eventbrite-organizer',
        NULL,
        'https://www.eventbrite.com/o/like-2-laugh-productions-1394222717',
        TRUE,
        ARRAY[]::text[]
    )
ON CONFLICT (name) DO UPDATE
SET slug = EXCLUDED.slug,
    website = EXCLUDED.website,
    scraping_url = EXCLUDED.scraping_url,
    visible = TRUE,
    show_name_keywords = EXCLUDED.show_name_keywords;

-- Organizer-mode rows must have no production_company_venues mappings: a mapped
-- production company uses the first mapped venue as a proxy, retaining that
-- venue's single-venue eventbrite_id and defeating organizer mode.
DELETE FROM production_company_venues AS pcv
USING production_companies AS pc
WHERE pc.id = pcv.production_company_id
  AND pc.slug IN (
      '13th-road-eventbrite-organizer',
      'comedy-party-eventbrite-organizer',
      'like-2-laugh-productions-eventbrite-organizer'
  );
