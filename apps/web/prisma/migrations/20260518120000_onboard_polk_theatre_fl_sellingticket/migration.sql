-- Onboard Polk Theatre Florida (club 2572) from temporary tour_dates
-- discovery to the generic SellingTicket scraper.
--
-- Verification on 2026-05-18:
--   * No existing active canonical duplicate found by Polk/Lakeland name,
--     polktheatre.org domain, or SellingTicket OrganizationID=64 source URL.
--   * Official site https://www.polktheatre.org/home lists Polk Theatre at
--     121 South Florida Ave., Lakeland, FL 33801 and links ticket purchasing
--     to secure.sellingticket.com with OrganizationID=64.
--   * The SellingTicket list page is fetchable with the scraper Playwright
--     stack and exposes server-rendered title, address, date/time, and buy URL
--     table rows.
--   * A read-only GenericSellingTicketScraper smoke run with conservative
--     include_title_patterns produced 2 comedy-relevant shows:
--       - Brincos Dieras pres. by Elite Entertainment (18+), 2026-05-29
--       - OMGITSWICKS & FRIENDS pres. by Brickhouse Comedy Prod., 2026-08-29

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 2572
          AND c.name = 'Polk Theatre Florida'
          AND c.city = 'Lakeland'
          AND c.state = 'FL'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND ss.id = 1580
          AND ss.platform = 'tour_dates'::"ScrapingPlatform"
          AND ss.scraper_key = 'tour_dates'
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Polk Theatre Florida: expected active tour_dates stub club 2572/source 1580 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE club_id <> 2572
          AND lower(source_url) LIKE '%secure.sellingticket.com%organizationid=64%'
          AND enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard Polk Theatre Florida: SellingTicket OrganizationID=64 is already assigned to another enabled source';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.polktheatre.org',
    address = '121 South Florida Avenue',
    zip_code = '33801',
    country = 'US',
    timezone = 'America/New_York'
WHERE id = 2572
  AND name = 'Polk Theatre Florida'
  AND city = 'Lakeland'
  AND state = 'FL'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-18',
            'replacement_platform', 'custom',
            'replacement_scraper_key', 'sellingticket',
            'replacement_source_url', 'https://secure.sellingticket.com/design22/clients/list/index_byUserListAll.aspx?OrganizationID=64',
            'rationale', 'Temporary tour_dates source replaced after verified SellingTicket scrape produced comedy-relevant shows.'
        )
    ),
    updated_at = NOW()
WHERE id = 1580
  AND club_id = 2572
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata,
    created_at,
    updated_at
)
VALUES (
    2572,
    'custom'::"ScrapingPlatform",
    'sellingticket',
    'https://secure.sellingticket.com/design22/clients/list/index_byUserListAll.aspx?OrganizationID=64',
    0,
    TRUE,
    jsonb_build_object(
        'include_title_patterns', jsonb_build_array(
            'comedy',
            'comedian',
            'comic',
            'brincos dieras',
            'leslie jones'
        ),
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-18',
            'official_site', 'https://www.polktheatre.org',
            'official_calendar', 'https://www.polktheatre.org/calendar',
            'ticket_list_url', 'https://secure.sellingticket.com/design22/clients/list/index_byUserListAll.aspx?OrganizationID=64',
            'sellingticket_organization_id', '64',
            'sample_events', jsonb_build_array(
                'Brincos Dieras pres. by Elite Entertainment (18+)',
                'OMGITSWICKS & FRIENDS pres. by Brickhouse Comedy Prod.'
            ),
            'verification', 'GenericSellingTicketScraper returned 2 comedy-relevant shows from the live SellingTicket list using include_title_patterns and excluded nonmatching film/music rows.'
        )
    ),
    NOW(),
    NOW()
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = scraping_sources.metadata || EXCLUDED.metadata,
    updated_at = NOW();

DO $$
BEGIN
    IF to_regclass('public.club_aliases') IS NOT NULL THEN
        INSERT INTO club_aliases (
            club_id,
            alias_name,
            normalized_alias_name,
            city,
            state,
            normalized_city,
            normalized_state,
            source,
            verified
        )
        VALUES
            (
                2572,
                'Polk Theatre Florida',
                'polk theatre florida',
                'Lakeland',
                'FL',
                'lakeland',
                'fl',
                '20260518120000: SellingTicket onboarding',
                TRUE
            ),
            (
                2572,
                'Polk Theatre',
                'polk theatre',
                'Lakeland',
                'FL',
                'lakeland',
                'fl',
                '20260518120000: SellingTicket onboarding',
                TRUE
            ),
            (
                2572,
                'Polk Theater',
                'polk theater',
                'Lakeland',
                'FL',
                'lakeland',
                'fl',
                '20260518120000: SellingTicket onboarding',
                TRUE
            )
        ON CONFLICT (normalized_alias_name, normalized_city, normalized_state)
        DO UPDATE SET
            club_id = EXCLUDED.club_id,
            alias_name = EXCLUDED.alias_name,
            city = EXCLUDED.city,
            state = EXCLUDED.state,
            source = EXCLUDED.source,
            verified = TRUE,
            updated_at = NOW();
    END IF;
END $$;
