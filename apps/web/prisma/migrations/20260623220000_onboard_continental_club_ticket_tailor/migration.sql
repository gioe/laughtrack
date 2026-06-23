-- Onboard Continental Club (Oakland, CA) via the existing ticket_tailor scraper - TASK-3216.
--
-- Continental Club is a historic West Oakland event hall (opened 1945 as Christy's
-- Grill) that self-markets a "comedy club" and once hosted the award-winning Comedy
-- Oakland stand-up series (East Bay Express "Best Comedy Night" 2016-2023, plus
-- legends Richard Pryor / Paul Mooney / Luenell). Its OWN ticketing runs on Ticket
-- Tailor: events.oaklandcontinentalclub.com is a CNAME to custom.tickettailor.com,
-- account slug `continentalclub`. The box-office listing sits behind Cloudflare and
-- clears via the dedicated ticket_tailor scraper (curl_cffi chrome impersonation +
-- the venue website Referer), so we avoid Playwright/json_ld entirely. Single-venue
-- mode attaches every (filtered) listing event to this club.
--
-- Mixed-use filter: the box office is overwhelmingly music/DJ/rave/private-party
-- programming (verified 2026-06-23: 7 upcoming events, all non-comedy: Sapphic Pride,
-- Rooftop Party, Afrobeats, Baby Rave, concerts). Comedy is intermittent and not
-- currently on sale. We therefore apply an opt-in `include_title_patterns` comedy
-- allowlist (TASK-3216 added it to TicketTailorScraper, mirroring ticketweb): the
-- scraper keeps only stand-up/comedy/showcase/open-mic/improv titles and drops the
-- music noise. This yields 0 shows today and auto-populates this club's comedy
-- shows when the next stand-up night is listed (Clayton Club precedent, TASK-3192).
-- A 0-show scrape here is EXPECTED, not a failure: the music feed is real and clean;
-- there is simply no comedy currently on the calendar.
--
-- Idempotent: guarded by NOT EXISTS on google_place_id / name (clubs) and
-- (club_id, scraper_key) (scraping_sources), so re-runs and fresh DBs converge.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Continental Club', '1658 12th St, Oakland, CA 94607, USA',
    'https://oaklandcontinentalclub.com/',
    'Oakland', 'CA', '94607', 'America/Los_Angeles', 'US', 'club',
    'ChIJV-4pnid-hYARwPm7FLiA4MA', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJV-4pnid-hYARwPm7FLiA4MA'
       OR name = 'Continental Club'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'ticket_tailor',
    'https://www.tickettailor.com/events/continentalclub/',
    TRUE,
    0,
    '{
        "account_slug": "continentalclub",
        "single_venue": true,
        "include_title_patterns": [
            "comedy",
            "stand[- ]?up",
            "comedian",
            "open mic",
            "improv",
            "showcase"
        ],
        "cloudflare_bypass": {
            "strategy": "ticket_tailor_curl_cffi_referer",
            "referer": "https://oaklandcontinentalclub.com/",
            "reason": "Ticket Tailor listing HTML clears Cloudflare via curl_cffi chrome impersonation plus the venue website Referer; the custom events.oaklandcontinentalclub.com domain is a CNAME to custom.tickettailor.com."
        },
        "onboarded_via": "TASK-3216: Continental Club self-markets a comedy club + historic Comedy Oakland series; own ticketing is Ticket Tailor (account continentalclub). Mixed-use box office (verified 2026-06-23: 7 upcoming events, all music/party, 0 comedy). include_title_patterns keeps only comedy; auto-populates when next stand-up night lists.",
        "dice_venue_id": "16308",
        "dice_note": "Continental Club also lists on DICE (venue id 16308, dice.fm/venue/continental-club-nv3g8) but currently only a single music/DJ event; Ticket Tailor is the venue-owned primary box office."
    }'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJV-4pnid-hYARwPm7FLiA4MA' OR c.name = 'Continental Club')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'ticket_tailor'
  );
