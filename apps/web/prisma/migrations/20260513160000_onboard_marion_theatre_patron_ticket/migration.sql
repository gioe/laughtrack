-- TASK-2169: Onboard Marion Theatre (Ocala FL) onto the generic
-- PatronTicketScraper introduced in TASK-2168.
--
-- Marion Theatre is a separate physical venue (50 S Magnolia Ave, downtown
-- Ocala FL 34471) operated by the same Ocala-FL ticketing org that runs
-- Reilly Arts Center (club_id=2368). Both venues are served by a single
-- Salesforce PatronTicket site at https://reillyartscenter.my.salesforce-sites.com/ticket;
-- a live fetchEvents API call on 2026-05-13 returned 83 total events across
-- two venue IDs, with Salesforce venue ID a0T4T0000005C4gUAE specifically
-- covering Marion Theatre programming (Steve-O, Tony Dabas, Natalie Cuomo,
-- the Sit Down for Stand Up series, etc.).
--
-- Marion Theatre is NOT yet in the clubs table — there is no pre-existing
-- tour_dates discovery row for it, so this migration only needs to:
--   1. INSERT the new clubs row
--   2. INSERT the patron_ticket scraping_sources row scoped to venue
--      ID a0T4T0000005C4gUAE
--
-- Criterion 4 of TASK-2169 ("Any pre-existing tour_dates discovery row for
-- Marion Theatre is demoted") is N/A because no such row exists.
WITH new_club AS (
    INSERT INTO clubs (
        name,
        address,
        website,
        city,
        state,
        zip_code,
        phone_number,
        timezone,
        country,
        club_type,
        status,
        visible
    )
    VALUES (
        'Marion Theatre',
        '50 S Magnolia Ave, Ocala, FL 34471',
        'https://www.reillyartscenter.com/themarion/',
        'Ocala',
        'FL',
        '34471',
        '(352) 820-3049',
        'America/New_York',
        'US',
        'club',
        'active',
        TRUE
    )
    ON CONFLICT (name) DO UPDATE
    SET address = EXCLUDED.address,
        website = EXCLUDED.website,
        city = EXCLUDED.city,
        state = EXCLUDED.state,
        zip_code = EXCLUDED.zip_code,
        phone_number = EXCLUDED.phone_number,
        timezone = EXCLUDED.timezone,
        country = EXCLUDED.country
    RETURNING id
)
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
SELECT
    new_club.id,
    'patron_ticket'::"ScrapingPlatform",
    'patron_ticket',
    'https://reillyartscenter.my.salesforce-sites.com/ticket',
    0,
    TRUE,
    jsonb_build_object(
        'patronticket_venue_id', 'a0T4T0000005C4gUAE',
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-13',
            'official_site', 'https://www.reillyartscenter.com/themarion/',
            'patronticket_host', 'reillyartscenter.my.salesforce-sites.com',
            'salesforce_venue_id', 'a0T4T0000005C4gUAE',
            'verification', 'Live fetchEvents API on 2026-05-13 returned 83 events across two venue IDs; a0T4T0000005C4gUAE covers Marion Theatre programming (Steve-O, Tony Dabas, Natalie Cuomo, Sit Down for Stand Up).'
        )
    ),
    NOW(),
    NOW()
FROM new_club
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = scraping_sources.metadata || EXCLUDED.metadata,
    updated_at = NOW();
