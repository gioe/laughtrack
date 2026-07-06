-- TASK-3564: triage lower-confidence Google Places comedy/improv candidates
-- from the 19103 / 100-mile discovery run.
--
-- Onboard only candidates with verified first-party, venue-owned calendars that
-- existing scrapers can ingest. Deny-list the remaining lower-confidence Google
-- Places hits so discovery does not keep surfacing services, festivals,
-- schools, non-comedy theaters, or unsupported calendar feeds as visible clubs.

WITH candidates AS (
    SELECT *
    FROM (
        VALUES
            (
                'Lancaster Improv Players',
                '16 S Prince St, Lancaster, PA 17603, USA',
                'https://www.lancasterimprovplayers.org/',
                '17603',
                '',
                'America/New_York',
                'Lancaster',
                'PA',
                'ChIJic7wlFglxokRl5sigzliBvA',
                'eventbrite',
                'eventbrite',
                'https://www.eventbrite.com',
                '18160289357',
                NULL,
                '{"exclude_classes": true}'::jsonb
            ),
            (
                'Shore Thing Theater',
                '66 S Main St Studio 1, Ocean Grove, NJ 07756, USA',
                'https://www.shorethingtheater.com/',
                '07756',
                '',
                'America/New_York',
                'Ocean Grove',
                'NJ',
                'ChIJSzKexYAnwokRxWhUQlv4JhA',
                'crowdwork',
                'crowdwork',
                'https://crowdwork.com/api/v2/shorethingtheater1/shows',
                NULL,
                NULL,
                '{"default_timezone": "America/New_York"}'::jsonb
            )
    ) AS v(
        name,
        address,
        website,
        zip_code,
        phone_number,
        timezone,
        city,
        state,
        google_place_id,
        platform,
        scraper_key,
        source_url,
        eventbrite_id,
        wix_event_id,
        metadata
    )
),
normalized_candidates AS (
    SELECT
        c.*,
        lower(regexp_replace(split_part(c.address, ',', 1), '[^a-zA-Z0-9]+', '', 'g')) AS street_key
    FROM candidates c
),
inserted_clubs AS (
    INSERT INTO clubs (
        name,
        address,
        website,
        zip_code,
        phone_number,
        popularity,
        timezone,
        city,
        state,
        country,
        google_place_id,
        visible,
        status,
        club_type
    )
    SELECT
        nc.name,
        nc.address,
        nc.website,
        nc.zip_code,
        nc.phone_number,
        0,
        nc.timezone,
        nc.city,
        nc.state,
        'US',
        nc.google_place_id,
        TRUE,
        'active',
        'club'
    FROM normalized_candidates nc
    WHERE NOT EXISTS (
        SELECT 1
        FROM clubs existing
        WHERE existing.name = nc.name
           OR existing.google_place_id = nc.google_place_id
           OR lower(regexp_replace(split_part(existing.address, ',', 1), '[^a-zA-Z0-9]+', '', 'g')) = nc.street_key
    )
    ON CONFLICT (name) DO NOTHING
    RETURNING id, name
),
preexisting_target_clubs AS (
    SELECT
        existing.id AS club_id,
        nc.name
    FROM normalized_candidates nc
    JOIN clubs existing
      ON existing.name = nc.name
      OR existing.google_place_id = nc.google_place_id
      OR lower(regexp_replace(split_part(existing.address, ',', 1), '[^a-zA-Z0-9]+', '', 'g')) = nc.street_key
),
target_clubs AS (
    SELECT
        COALESCE(ic.id, ptc.club_id) AS club_id,
        nc.platform,
        nc.scraper_key,
        nc.source_url,
        nc.eventbrite_id,
        nc.wix_event_id,
        nc.metadata
    FROM normalized_candidates nc
    LEFT JOIN inserted_clubs ic ON ic.name = nc.name
    LEFT JOIN preexisting_target_clubs ptc ON ptc.name = nc.name
    WHERE COALESCE(ic.id, ptc.club_id) IS NOT NULL
)
INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    eventbrite_id,
    wix_event_id,
    priority,
    enabled,
    metadata
)
SELECT
    tc.club_id,
    tc.platform::"ScrapingPlatform",
    tc.scraper_key,
    tc.source_url,
    tc.eventbrite_id,
    tc.wix_event_id,
    0,
    TRUE,
    tc.metadata
FROM target_clubs tc
WHERE NOT EXISTS (
    SELECT 1
    FROM scraping_sources ss
    WHERE ss.club_id = tc.club_id
      AND ss.enabled = TRUE
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET
    scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    eventbrite_id = EXCLUDED.eventbrite_id,
    wix_event_id = EXCLUDED.wix_event_id,
    enabled = TRUE,
    metadata = EXCLUDED.metadata,
    updated_at = NOW()
WHERE scraping_sources.enabled = FALSE;

INSERT INTO venue_deny_list (
    google_place_id,
    name,
    reason,
    google_primary_type,
    evidence,
    added_by,
    denied_at
)
VALUES
    (
        'ChIJn_32dGLIxokRzEq4a9ukiVg',
        'Comedy On The Waterfront',
        'Eventbrite organizer/service, not a venue-owned comedy club calendar',
        'service',
        '{"task":"TASK-3564","address":"325 N Christopher Columbus Blvd, Philadelphia, PA 19106","website":"http://www.eventbrite.com/o/nsw-media-group-817558125","disposition":"deny_listed_aggregator_or_producer","evidence":"Eventbrite organizer 817558125 is NSW Media Group; Google primary_type=service and address is not a dedicated club."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJtaYWLQK7xokRnlOdDyVT9jc',
        'Improv Ambler',
        'No website or supported venue-owned calendar found',
        'performing_arts_theater',
        '{"task":"TASK-3564","address":"85 E Butler Ave, Ambler, PA 19002","website":null,"disposition":"deny_listed_no_supported_calendar","evidence":"No first-party website was present in Google Places for verification or scraper configuration."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJf0D4MIwuE60RnijYpKmk98E',
        'Vince Valentine''s Comedy Collective',
        'Mobile/private comedy service, not a fixed public venue calendar',
        'service',
        '{"task":"TASK-3564","address":"45 Manchester Rd, Sewell, NJ 08080","website":"https://www.vvcomedy.com/","disposition":"deny_listed_non_venue_service","evidence":"Site describes comedy shows that come to corporate and private events, not a venue-owned public calendar."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJgywfGpgCxIkRLQDMoaSCI-A',
        'Poco''s Restaurant, Bar & Comedy Cabaret',
        'Comedy Cabaret calendar uses unsupported PatronBase ticketing',
        'restaurant',
        '{"task":"TASK-3564","address":"625 N Main St, Doylestown, PA 18901","website":"https://pocos.com/","disposition":"deny_listed_unsupported_calendar","evidence":"Poco''s links to Comedy Cabaret Doylestown; ticket links are us.patronbase.com, which is not covered by the existing PatronTicket scraper."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJ6ZUhkxN3xokRrX3m_eUMZrg',
        'Al''s Diamond Cabaret',
        'Adult nightclub/employment page, not a comedy venue calendar',
        'night_club',
        '{"task":"TASK-3564","address":"1810 N 5th St, Reading, PA 19601","website":"https://alsdiamondcabaret.com/employment/","disposition":"deny_listed_non_comedy","evidence":"Website is an adult cabaret employment page with no comedy show calendar."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJ__-_XRyTw4kRlIUYIyqYqYs',
        'Gemini Comedy Entertainment',
        'Entertainer booking service, not a venue-owned public calendar',
        'service',
        '{"task":"TASK-3564","address":"6 Commerce St, Somerville, NJ 08876","website":"http://www.geminicomedy.com/","disposition":"deny_listed_non_venue_service","evidence":"Site presents magic/comedy/ventriloquism entertainment services and private bookings rather than a fixed club calendar."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJ8XmUB3ttxIkRFCWK9GzGr1U',
        'Good Human Improv Company',
        'Improv classes/training with no supported scrapeable show feed',
        'performing_arts_theater',
        '{"task":"TASK-3564","address":"916 Northampton St, Easton, PA 18042","website":"https://www.goodhumanimprov.com/","disposition":"deny_listed_no_supported_calendar","evidence":"First-party site focuses on classes and corporate training; events/show pages did not expose a supported scraper platform."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJdY6-06R_wYkRILNJq1CyPSw',
        'Comedian Joseph Anthony',
        'Individual comedian service listing, not a venue',
        'service',
        '{"task":"TASK-3564","address":"53 Sami Dr, Howell Township, NJ 07731","website":"https://www.fiverr.com/crookedviews","disposition":"deny_listed_individual_comedian","evidence":"Google result points to an individual comedian/Fiverr service, not a public venue calendar."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJbQ7H5ULGw4kRuz5PzjeMf0M',
        'Cabaret Theatre (Rutgers University)',
        'Student theater, not a comedy club calendar',
        'performing_arts_theater',
        '{"task":"TASK-3564","address":"7 Suydam St, New Brunswick, NJ 08901","website":"http://www.cabarettheatre.org/","disposition":"deny_listed_non_comedy_theater","evidence":"Student theater site/ticketing is not a dedicated comedy or improv venue calendar."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJiRq8aPAnwokRVp6ZfFWpcIE',
        'Improv 4 Life',
        'Education/classes organization, not a venue-owned comedy calendar',
        'association_or_organization',
        '{"task":"TASK-3564","address":"1700 Main St, Lake Como, NJ 07719","website":"https://improv4life.org/","disposition":"deny_listed_education","evidence":"Site is oriented around classes and uses Mindbody links; no venue-owned public comedy show feed was found."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJQxTE9KNZwokR8uQW5AxR6jY',
        'Letter of Marque Theater Co. & Brooklyn Improv Training',
        'Theater/training organization, not a dedicated comedy club calendar',
        'association_or_organization',
        '{"task":"TASK-3564","address":"103 10th St, Brooklyn, NY 11215","website":"http://www.lomtheater.org/","disposition":"deny_listed_theater_training","evidence":"First-party site combines theater company and improv training; ticketing is mixed Zeffy/OvationTix and not a venue-owned comedy club feed."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJ8UmkZaNZwokR6bkotwn3W20',
        'Improvolution',
        'Improv school/training venue without a supported calendar feed',
        'performing_arts_theater',
        '{"task":"TASK-3564","address":"115 MacDougal St, New York, NY 10012","website":"https://www.improvolution.org/","disposition":"deny_listed_no_supported_calendar","evidence":"Squarespace site focuses on classes and shows but did not expose a supported Squarespace/API calendar source."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJUbHGFJcEyIkR9mJTV97VFD4',
        'Drop Three Improv and Sketch Comedy',
        'Improv/sketch group with no supported venue-owned calendar feed',
        'association_or_organization',
        '{"task":"TASK-3564","address":"7911 Harford Rd, Parkville, MD 21234","website":"http://www.dropthree.com/","disposition":"deny_listed_no_supported_calendar","evidence":"Site did not expose a supported public show calendar; result is an organization/group rather than a fixed club."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJY_fFGbtZwokRkUXAJ3IZBGI',
        'Manhattan Comedy School',
        'Comedy school/classes, not a public club calendar',
        'educational_institution',
        '{"task":"TASK-3564","address":"500 8th Ave, New York, NY 10018","website":"http://www.manhattancomedyschool.com/","disposition":"deny_listed_education","evidence":"Site is a comedy school/classes listing rather than a venue-owned recurring public show calendar."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJmTJDjwZZwokRFDMJV7vXHqw',
        'Amateur Comedy Club',
        'Wix event feed contains non-comedy theater programming',
        'association_or_organization',
        '{"task":"TASK-3564","address":"150 E 36th St, New York, NY 10016","website":"http://www.amateurcomedyclub.org/","disposition":"deny_listed_non_comedy_feed","evidence":"Wix smoke test returned five Summer Make Believe theater performances rather than comedy/improv shows."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJK6eJyERZwokRVLbeM4_T7XY',
        'Greenpoint Comedy Club',
        'No currently fetchable supported ticket/calendar source',
        'bar',
        '{"task":"TASK-3564","address":"66 Greenpoint Ave, Brooklyn, NY 11222","website":"https://www.greenpointcomedyclub.com/","disposition":"deny_listed_no_supported_calendar","evidence":"First-party site links to tickets.greenpointcomedyclub.com, but the ticket host did not resolve during triage and no supported feed could be configured."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJWYwvFFZYwokRBKYkswODxNk',
        'New York Comedy Festival',
        'Festival/corporate office, not a fixed venue',
        'corporate_office',
        '{"task":"TASK-3564","address":"1626 Broadway, New York, NY 10019","website":"http://www.nycomedyfestival.com/","disposition":"deny_listed_festival","evidence":"Festival listing is not a venue-owned club calendar and should not create a visible club for the corporate office address."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJFWmwnldYwokRZRfoD31ocYo',
        'Improv 4 Kids',
        'Children/teen educational programming, not a venue-owned club calendar',
        'performing_arts_theater',
        '{"task":"TASK-3564","address":"318 W 53rd St, New York, NY 10019","website":"http://improv4kids.com/","disposition":"deny_listed_education","evidence":"OvationTix smoke test returned 49 Comedy 4 Teens/education-style events rather than a comedy club calendar."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJya-DOwJZwokRuyaGKO3MhTs',
        'IMPROV',
        'Defensive driving business, not a comedy venue',
        'uncategorized',
        '{"task":"TASK-3564","address":"575 Lexington Ave 4th floor, New York, NY 10022","website":"https://www.myimprov.com/defensive-driving/new-york","disposition":"deny_listed_non_comedy","evidence":"URL is myimprov.com defensive driving, not a comedy/improv show venue."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJ1XBCLcAEyIkRRO83Sg1QWh4',
        'Baltimore Comedy Festival',
        'Festival/corporate office without venue-owned calendar',
        'corporate_office',
        '{"task":"TASK-3564","address":"120 W North Ave, Baltimore, MD 21201","website":null,"disposition":"deny_listed_festival","evidence":"Google result is a festival/corporate office with no website in the candidate data and no fixed venue calendar."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJre21q50EyIkRMAAFZPZjnXU',
        'The Red Room Cabaret',
        'No website or supported comedy calendar found',
        'uncategorized',
        '{"task":"TASK-3564","address":"411 E Baltimore St, Baltimore, MD 21202","website":null,"disposition":"deny_listed_no_supported_calendar","evidence":"Candidate has no website in Google Places and no verified scrapeable venue-owned calendar."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJ5Y1KUT7ByIkRt4x3FBi9AOw',
        'Harrisburg Improv Theatre',
        'No supported scrapeable show feed found',
        'performing_arts_theater',
        '{"task":"TASK-3564","address":"1633 N 3rd St, Harrisburg, PA 17102","website":"http://www.hbgimprov.com/","disposition":"deny_listed_no_supported_calendar","evidence":"Squarespace products smoke test returned zero parseable shows because product titles did not contain dates; no supported calendar source was available."}'::jsonb,
        'TASK-3564',
        NOW()
    ),
    (
        'ChIJl_YYnY17wokRb0a28hkQiaM',
        'Long Island Improv',
        'Education/classes site, not a venue-owned public show calendar',
        'educational_institution',
        '{"task":"TASK-3564","address":"228 S Ocean Ave, Freeport, NY 11520","website":"http://longislandimprov.com/","disposition":"deny_listed_education","evidence":"Weebly site is oriented around improv education/classes and did not expose a supported public show feed."}'::jsonb,
        'TASK-3564',
        NOW()
    )
ON CONFLICT (google_place_id) DO UPDATE
SET
    name = EXCLUDED.name,
    reason = EXCLUDED.reason,
    google_primary_type = EXCLUDED.google_primary_type,
    evidence = EXCLUDED.evidence,
    added_by = EXCLUDED.added_by;
