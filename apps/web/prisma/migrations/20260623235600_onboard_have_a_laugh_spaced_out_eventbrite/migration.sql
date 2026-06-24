-- Onboard "Have a Laugh" / "Spaced Out Comedy" (San Jose, CA) as an Eventbrite
-- organizer-mode production_company - TASK-3226.
--
-- Discovery (discover-comedy-venues near 94101 SF) tagged "Have A Laugh Comedy
-- Shows" to 1788 N First St #10, San Jose with Google primary_type=comedy_club,
-- but that address is The Province (an Asian-fusion restaurant inside Bay 101
-- Casino), not a comedy room -- it is merely one of the rotating spaces this
-- producer has used. "Have a Laugh" is an independent San Jose comedy PRODUCER
-- with no room of its own: it runs the recurring "Spaced Out: Standup Comedy"
-- series via a single Eventbrite organizer, "Spaced Out Comedy"
-- (organizer id 80647104493), at many rotating downtown-San-Jose rooms --
-- e.g. Mysterieux Brand (San Pedro Square), Mosaic Restaurant & Lounge,
-- Island Taste Caribbean Grill, Narrative Fermentations, 28 North Almaden Ave.
-- Onboarding it as a single fixed club at The Province would mis-attribute every
-- rotating-venue show to that one restaurant address.
--
-- Resolution: producer, not venue. Modeled as a no-mapping Eventbrite
-- organizer-mode production company (the Best Medicine Comedy / TASK-3214
-- pattern, itself the TASK-2108 Riot/Backdoor/Comet pattern). ScrapingService
-- synthesizes an in-memory organizer proxy from production_companies.scraping_url,
-- EventbriteScraper organizer mode groups events by venue, and
-- ClubHandler.upsert_for_eventbrite_venue routes each show to the correct
-- auto-created per-venue club -- those per-venue clubs are the browsable surfaces.
--
-- visible=TRUE here means SCRAPE-ENABLED: ProductionCompanyHandler
-- .get_all_production_companies() only loads visible production companies, so an
-- organizer-mode producer must be visible=TRUE to be scraped at all (matching the
-- working Best Medicine Comedy / Riot / Backdoor / Comet rows).
-- show_name_keywords is empty: the organizer feed is curated all-comedy (the
-- "Spaced Out" standup series), so no title filter is needed.
--
-- Verified 2026-06-23: a real organizer-mode scrape of org 80647104493 returned
-- the upcoming comedy show "Spaced Out: Standup Comedy in Downtown San Jose"
-- (2026-07-26) at Mysterieux Brand, San Jose.

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
        'Have a Laugh',
        'have-a-laugh-spaced-out-eventbrite-organizer',
        'https://www.eventbrite.com/o/spaced-out-comedy-80647104493',
        'https://www.eventbrite.com/o/spaced-out-comedy-80647104493',
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
  AND pc.slug = 'have-a-laugh-spaced-out-eventbrite-organizer';
