-- TASK-3023: Onboard Milwaukee Comedy as a Ticket Tailor production company.
--
-- Milwaukee Comedy, LLC (milwaukeecomedy.com) is a roving comedy PRODUCTION
-- COMPANY — it runs shows at varying physical venues (Vendetta Coffee Bar,
-- Lakefront Brewery, etc.), selling through a single Ticket Tailor box office
-- (account slug 'milwaukeecomedy').
--
-- Modeling it as a row in `production_companies` (with NO production_company_venues
-- row) routes it through ScrapingService._scrape_production_companies, which
-- detects the empty venue mapping and synthesizes an in-memory Club proxy from
-- the scraping_url. _build_synthetic_proxy_for_company now recognizes Ticket
-- Tailor box-office URLs (alongside Eventbrite organizers) and drives the
-- new TicketTailorScraper, which groups the box office's events by their
-- per-event venue and upserts one `clubs` row per distinct venue via
-- ClubHandler.upsert_discovered_venue. Each resulting Show is tagged with
-- production_company_id so the Milwaukee Comedy brand is preserved without
-- forcing every event under a single fake venue club.
--
-- visible=FALSE: Milwaukee Comedy is a hidden proxy producer — its shows
-- surface under the auto-created per-venue clubs, not under a producer page.
-- The website is used as the Cloudflare-clearing Referer by the scraper.
--
-- show_name_keywords is empty: the Ticket Tailor box office is curated by
-- Milwaukee Comedy itself, so every event in it is theirs (no name filtering).
--
-- NOTE: 'The Laughing Tap' (laughingtap.com) is a SEPARATE fixed venue — do not
-- merge identities; triage separately.

INSERT INTO production_companies (
    name,
    slug,
    scraping_url,
    website,
    visible,
    show_name_keywords
)
VALUES (
    'Milwaukee Comedy',
    'milwaukee-comedy',
    'https://www.tickettailor.com/events/milwaukeecomedy/',
    'https://www.milwaukeecomedy.com/',
    FALSE,
    ARRAY[]::text[]
)
ON CONFLICT (name) DO UPDATE
   SET slug = EXCLUDED.slug,
       scraping_url = EXCLUDED.scraping_url,
       website = EXCLUDED.website,
       visible = EXCLUDED.visible;
