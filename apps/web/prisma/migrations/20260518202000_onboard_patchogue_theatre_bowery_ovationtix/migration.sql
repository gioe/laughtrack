-- Onboard Patchogue Theatre for the Performing Arts (club 2577) from temporary
-- tour_dates discovery to a venue-specific Bowery+OvationTix scraper.
--
-- Discovered from Leslie Jones tour evidence:
--   https://concerts50.com/buy/leslie-jones-in-patchogue-tickets-oct-08-2026
--
-- Verification on 2026-05-18:
--   * OvationTix client 34780's generic calendar feed
--     (web.ovationtix.com/trs/cal/34780) is incomplete: it returns only three
--     productions (Buckethead, Samantha Fish, Be Like Blippi) and omits every
--     Bowery-listed comedy date including the Leslie Jones show
--     (performance 11795830, production 1272458, 2026-10-08 20:00).
--   * The Bowery Presents venue listing
--     (https://www.bowerypresents.com/venues/patchogue-theatre) carries direct
--     ci.ovationtix.com/34780/performance/<id> deep-links to every confirmed
--     date.
--   * Read-only PatchogueTheatreScraper run with ovationtix_id=34780 and the
--     Bowery URL extracted 10 performance links, fetched each via the
--     Performance({id}) endpoint, applied the
--     comedian/stand-up/comic keyword filter, and produced 2 upcoming
--     comedy shows (Leslie Jones, Ben Bankas) with full per-tier pricing
--     (8 sections each). The 8 non-comedy events (Amy Grant, Old Crow Medicine
--     Show, Little Shop of Horrors, Ann Wilson, Johnnyswim, Yächtley Crëw,
--     Blue Öyster Cult, ELP tribute) were correctly filtered out.

DO $$
BEGIN
    -- Guard 1: club identity is still what we onboarded against.
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        WHERE c.id = 2577
          AND c.name = 'Patchogue Theatre for the Performing Arts'
          AND c.city = 'Patchogue'
          AND c.state = 'NY'
          AND COALESCE(c.visible, TRUE) = TRUE
          AND c.status = 'active'
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Patchogue Theatre club 2577: club identity has changed';
    END IF;

    -- Guard 2: the temporary tour_dates row we are replacing is still in place.
    -- Without this guard, a previous re-route would silently get clobbered.
    IF NOT EXISTS (
        SELECT 1
        FROM scraping_sources ss
        WHERE ss.id = 1585
          AND ss.club_id = 2577
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Patchogue Theatre club 2577: expected tour_dates source 1585 is missing or already replaced';
    END IF;

    -- Guard 3: OvationTix client 34780 is not already mapped to another club.
    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE platform = 'ovationtix'::"ScrapingPlatform"
          AND ovationtix_id = '34780'
          AND club_id <> 2577
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Patchogue Theatre: OvationTix client 34780 is already assigned to another club';
    END IF;
END $$;

-- Disable (do not delete) the temporary tour_dates source. Keeping the row
-- preserves the audit trail (last_seen_at, comedian refs) for retrospective
-- analysis while ensuring the engine no longer picks it as a fallback.
UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-18',
            'replacement_platform', 'ovationtix',
            'replacement_scraper_key', 'patchogue_theatre',
            'replacement_ovationtix_id', '34780',
            'replacement_source_url', 'https://www.bowerypresents.com/venues/patchogue-theatre',
            'rationale', 'Temporary tour_dates source replaced after verified Bowery+OvationTix scrape produced Leslie Jones (perf 11795830) and Ben Bankas (perf 11805262) with full per-tier pricing.'
        )
    ),
    updated_at = NOW()
WHERE id = 1585
  AND club_id = 2577
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    ovationtix_id,
    source_url,
    priority,
    enabled,
    metadata,
    created_at,
    updated_at
)
VALUES (
    2577,
    'ovationtix'::"ScrapingPlatform",
    'patchogue_theatre',
    '34780',
    'https://www.bowerypresents.com/venues/patchogue-theatre',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-18',
            'official_site', 'https://www.patchoguetheatre.org',
            'bowery_listing_url', 'https://www.bowerypresents.com/venues/patchogue-theatre',
            'ovationtix_client_id', '34780',
            'discovery_rationale', 'web.ovationtix.com/trs/cal/34780 calendar feed returns only 3 non-comedy productions and is missing every Bowery-listed comedy date; the Bowery listing carries direct ci.ovationtix.com/34780/performance/<id> deep-links to every confirmed date.',
            'sample_performance_id', '11795830',
            'sample_production_id', '1272458',
            'sample_show', 'Leslie Jones: I’m Hot Tour — 2026-10-08 20:00',
            'verification', 'PatchogueTheatreScraper extracted 10 performance links from Bowery, fetched each via Performance({id}), applied the comedian/stand-up/comic filter, and produced 2 comedy shows (Leslie Jones, Ben Bankas) with 8 ticket tiers each.'
        )
    ),
    NOW(),
    NOW()
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    ovationtix_id = EXCLUDED.ovationtix_id,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = scraping_sources.metadata || EXCLUDED.metadata,
    updated_at = NOW();
