-- Onboard Best Medicine Comedy (San Francisco, CA) as an Eventbrite
-- organizer-mode production_company - TASK-3214.
--
-- Best Medicine Comedy (bestmedicinecomedy.com) is an independent SF comedy
-- PRODUCER, not a fixed venue. Discovery tagged it to 240 Sanchez St with
-- Google primary_type=comedy_club, but the producer has no room of its own: its
-- own site links every show out to a single Eventbrite organizer,
-- "Best Medicine Comedy" (organizer id 26380464595), and those shows run at many
-- rotating SF rooms -- e.g. San Francisco Comedy Underground, Haight Laughsbury
-- Comedy Show, Bit City Comedy at Mr. Bing's, Noe Valley Farms, O'Reilly's Pub
-- (1828 Castro St / 1840 Haight St / 201 Columbus Ave / 2032 Polk St). Onboarding
-- it as a single fixed club would mis-attribute every show to one address.
--
-- Resolution: producer, not venue. Modeled as a no-mapping Eventbrite
-- organizer-mode production company (the TASK-2108 Riot/Backdoor/Comet pattern,
-- mirrored by the TASK-3156 Boston producers): ScrapingService synthesizes an
-- in-memory organizer proxy from production_companies.scraping_url,
-- EventbriteScraper organizer mode groups events by venue, and
-- ClubHandler.upsert_for_eventbrite_venue routes each show to the correct
-- auto-created per-venue club -- those per-venue clubs are the browsable surfaces.
--
-- visible=TRUE here means SCRAPE-ENABLED: ProductionCompanyHandler
-- .get_all_production_companies() only loads visible production companies, so an
-- organizer-mode producer must be visible=TRUE to be scraped at all (matching the
-- working TASK-2108 rows Riot/Backdoor/Comet; the visible=FALSE rows like
-- Milwaukee Comedy / Whale City are intentionally disabled). show_name_keywords
-- is empty: the organizer feed is all-comedy (curated by the producer), so no
-- title filter is needed.
--
-- Verified 2026-06-23: a real organizer-mode scrape of org 26380464595 returned
-- 92 upcoming comedy shows across the rotating SF venues.

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
        'Best Medicine Comedy',
        'best-medicine-comedy-eventbrite-organizer',
        'https://www.bestmedicinecomedy.com/',
        'https://www.eventbrite.com/o/best-medicine-comedy-26380464595',
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
  AND pc.slug = 'best-medicine-comedy-eventbrite-organizer';
