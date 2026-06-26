-- Onboard Moxi Theater (Greeley, CO) via the existing json_ld scraper - TASK-3425.
--
-- DRAFT pending parent verification: this background sandbox denied make/scrape/DB
-- execution, so the end-to-end `make scrape-club-id` gate (N>0) has NOT yet been
-- run. Everything else (live-site comedy confirmation, platform identification,
-- scraper mapping, JSON-LD field/date compatibility) is verified statically below.
--
-- Moxi Theater (moxitheater.com) is a fixed live-music concert hall at 802 9th St,
-- Greeley, CO 80631 (Google primary_type=concert_hall). Its own Webflow site
-- server-renders one schema.org Event JSON-LD block per upcoming show on the
-- HOMEPAGE (https://www.moxitheater.com/) — 30 inline `@type:Event` blocks, each
-- carrying name + startDate ("Mon DD, YYYY") + location + performer + an `offers`
-- block whose `url` is the Tixr checkout link (tixr.com/e/{id}) and `price`. The
-- generic json_ld scraper reads these with a plain static fetch:
--   * parse_event_date() handles the "%b %d, %Y" date-only startDate format;
--   * JsonLdEvent._validate_required_fields() falls back to offers.url when there
--     is no top-level url, so the Tixr link becomes show_page_url — no DataDome-
--     sensitive Tixr detail fetch is performed (default single-page json_ld flow).
-- The site's /event-calendar page is JS-rendered (0 inline JSON-LD) and its
-- /events page links a SHARED "Bandwagon" Tixr group (also lists The Black Buzzard,
-- Denver — see migration 20260625163800), so source_url intentionally points at the
-- HOMEPAGE, which carries only Moxi's own events.
--
-- Confirmed stand-up comedy at this venue (verified 2026-06-26 via the live
-- homepage JSON-LD), alongside mostly-music programming (Corb Lund, Texas Hippie
-- Coalition, Drivin N Cryin, etc.):
--   * "John Caparulo - Mad Cap Comedy"            2026-07-09  (tixr.com/e/189469)
--   * "Kim Congdon, Dulce Mac (Stand-Up Comedy)"  2026-07-23  (tixr.com/e/193615)
--   * "Jeff Dye - Stand Up Comedy (Early Show)"   2026-09-10  (tixr.com/e/184820)
--   * "Alex Dragicevich - Stand Up Comedy"        2026-08-06  (tixr.com/e/186873)
--   * "Chris Higgins Stand Up Comedy at Moxi"     2026-08-27  (tixr.com/e/189950)
--   * "Underground Comedy Showcase: David Testroet" 2026-07-02 (tixr.com/e/190713)
--   * "Underground Comedy Showcase: Max Meisel..."  2026-07-16 (tixr.com/e/184111)
--   (7 comedy of 30 homepage events; all match the comedy keyword/allowlist.)
--
-- Because the venue is MIXED-USE (concert hall) and the JSON-LD carries no genre,
-- metadata.comedy_filter=true isolates comedy via the shared select_comedy_titles
-- heuristic (keyword OR allowlist OR known comedian). The 7 stand-up titles survive
-- on the "comedy"/"stand-up"/"comedian" keyword; the ~23 music events are dropped.
--
-- Fixed venue (the club is its own room) -> visible=TRUE.
-- Idempotent: guarded by NOT EXISTS on google_place_id / name (clubs) and
-- (club_id, scraper_key) (scraping_sources), so re-runs and fresh DBs converge.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Moxi Theater', '802 9th St, Greeley, CO 80631, USA',
    'http://www.moxitheater.com/',
    'Greeley', 'CO', '80631', 'America/Denver', 'US', 'club',
    'ChIJOcN51iWibocR4hyENQQmEog', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJOcN51iWibocR4hyENQQmEog'
       OR name = 'Moxi Theater'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://www.moxitheater.com/',
    TRUE,
    0,
    '{
        "comedy_filter": true,
        "onboarded_via": "TASK-3425: Moxi Theater (Greeley, CO) is a mixed-use concert hall whose own Webflow homepage server-renders one schema.org Event JSON-LD block per show (name + startDate + offers.url Tixr link + price). The generic json_ld scraper reads it statically (default single-page flow, offers.url fallback -> no DataDome Tixr detail fetch). comedy_filter isolates stand-up on the genre-less feed. Confirmed comedy 2026-06-26: John Caparulo (2026-07-09), Kim Congdon (2026-07-23), Jeff Dye (2026-09-10), Alex Dragicevich (2026-08-06), Chris Higgins (2026-08-27), Underground Comedy Showcase (2026-07-02/16)."
    }'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJOcN51iWibocR4hyENQQmEog' OR c.name = 'Moxi Theater')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );
