-- TASK-3166: Onboard Whale City Comedy as a Ticket Tailor production company.
--
-- Whale City Comedy (whalecitycomedy.com; New Bedford, MA) is a roving comedy
-- PRODUCTION COMPANY — it runs pop-up shows at varying physical venues (Society
-- Coffee Bar, galleryx_nb, local breweries), selling through a single Ticket
-- Tailor box office (account slug 'whalecitycomedy'). It is NOT a fixed club.
--
-- Modeling it as a row in `production_companies` (with NO production_company_venues
-- row) routes it through ScrapingService._scrape_production_companies, which
-- detects the empty venue mapping and synthesizes an in-memory Club proxy from
-- the scraping_url. _build_synthetic_proxy_for_company recognizes Ticket Tailor
-- box-office URLs and drives TicketTailorScraper, which groups the box office's
-- events by their per-event venue and upserts one `clubs` row per distinct venue
-- via ClubHandler.upsert_discovered_venue. Each Show is tagged with
-- production_company_id so the Whale City Comedy brand is preserved without
-- forcing every event under a single fake venue club. Mirrors the Milwaukee
-- Comedy onboarding (TASK-3023, migration 20260620).
--
-- visible=FALSE: Whale City Comedy is a hidden proxy producer — its shows
-- surface under the auto-created per-venue clubs, not under a producer page.
-- The website is used as the Cloudflare-clearing Referer by the scraper.
--
-- show_name_keywords is empty: the Ticket Tailor box office is curated by Whale
-- City Comedy itself, so every event in it is theirs (no name filtering).
--
-- NOTE: the box office is CURRENTLY EMPTY ("No events currently listed"), so a
-- scrape returns 0 shows until they post new dates. The shared TicketTailor card
-- selector (`li.events-listing__item`) was validated against a populated box
-- office (live tickettailor.com/events/milwaukeecomedy/ + the recorded fixture
-- in tests/scrapers/implementations/ticket_tailor/), so no Whale-City-specific
-- code is needed; the nightly scrape will pick up events automatically once
-- posted.

INSERT INTO production_companies (
    name,
    slug,
    scraping_url,
    website,
    visible,
    show_name_keywords
)
VALUES (
    'Whale City Comedy',
    'whale-city-comedy',
    'https://www.tickettailor.com/events/whalecitycomedy/',
    'https://whalecitycomedy.com/',
    FALSE,
    ARRAY[]::text[]
)
ON CONFLICT (name) DO UPDATE
   SET slug = EXCLUDED.slug,
       scraping_url = EXCLUDED.scraping_url,
       website = EXCLUDED.website,
       visible = EXCLUDED.visible;
