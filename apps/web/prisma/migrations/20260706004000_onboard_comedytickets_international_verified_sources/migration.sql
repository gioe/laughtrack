-- TASK-3590: onboard verified first-party/supported sources from the
-- ComedyTickets international candidate set.
--
-- ComedyTickets is used only as a discovery signal. The enabled rows below
-- were verified against first-party venue sites and smoke-tested with existing
-- scraper code:
--   * Boom Chicago: Ticketmaster focused comedy scraper, 19 future shows.
--   * Laugh Shop Calgary: Showpass generic scraper, 21 future shows.
--   * International mixed venues below: Ticketmaster focused comedy scraper,
--     5-39 future shows each.
--
-- Duplicate guard: do not insert a club when either the canonical name already
-- exists or another row has the same normalized street-number/street-name key.
-- Do not attach a source to a club that already has any enabled source.

WITH candidates AS (
    SELECT *
    FROM (
        VALUES
            (
                'Boom Chicago',
                'Rozengracht 117, 1016 LV Amsterdam, Netherlands',
                'https://boomchicago.nl',
                '1016 LV',
                '',
                'Europe/Amsterdam',
                'Amsterdam',
                '',
                'NL',
                52.37282,
                4.87902,
                TRUE,
                'club',
                'ticketmaster',
                'ticketmaster_comedy',
                'https://www.ticketmaster.com',
                'Z598xZbpZ7Fvk',
                '{}'::jsonb
            ),
            (
                '3Arena',
                'East Link Bridge, North Wall Quay, Dublin 1, Ireland',
                'https://3arena.ie',
                'Dublin 1',
                '',
                'Europe/Dublin',
                'Dublin',
                '',
                'IE',
                53.347512,
                -6.228482,
                TRUE,
                'venue',
                'ticketmaster',
                'ticketmaster_comedy',
                'https://www.ticketmaster.com',
                'KovZ9177WYV',
                '{}'::jsonb
            ),
            (
                'Bristol Hippodrome',
                'St. Augustine''s Parade, Bristol BS1 4UZ, United Kingdom',
                'https://www.atgtickets.com/venues/bristol-hippodrome/',
                'BS1 4UZ',
                '',
                'Europe/London',
                'Bristol',
                '',
                'GB',
                51.453183,
                -2.598389,
                TRUE,
                'venue',
                'ticketmaster',
                'ticketmaster_comedy',
                'https://www.ticketmaster.com',
                'KovZ9177Y7f',
                '{}'::jsonb
            ),
            (
                'Edinburgh Playhouse',
                '18-22 Greenside Place, Edinburgh EH1 3AA, United Kingdom',
                'https://www.atgtickets.com/venues/edinburgh-playhouse/',
                'EH1 3AA',
                '',
                'Europe/London',
                'Edinburgh',
                '',
                'GB',
                55.95704,
                -3.185041,
                TRUE,
                'venue',
                'ticketmaster',
                'ticketmaster_comedy',
                'https://www.ticketmaster.com',
                'KovZ9177mi7',
                '{}'::jsonb
            ),
            (
                'Eventim Apollo',
                '45 Queen Caroline Street, Hammersmith, London W6 9QH, United Kingdom',
                'https://www.eventimapollo.com/',
                'W6 9QH',
                '',
                'Europe/London',
                'London',
                '',
                'GB',
                51.490693,
                -0.224423,
                TRUE,
                'venue',
                'ticketmaster',
                'ticketmaster_comedy',
                'https://www.ticketmaster.com',
                'KovZpZAtadaA',
                '{}'::jsonb
            ),
            (
                'O2 Apollo Manchester',
                'Stockport Road, Manchester M12 6AP, United Kingdom',
                'https://www.academymusicgroup.com/o2apollomanchester/',
                'M12 6AP',
                '',
                'Europe/London',
                'Manchester',
                '',
                'GB',
                53.469422,
                -2.221964,
                TRUE,
                'venue',
                'ticketmaster',
                'ticketmaster_comedy',
                'https://www.ticketmaster.com',
                'KovZ9177YPV',
                '{}'::jsonb
            ),
            (
                'Club Regent Event Centre',
                '1425 Regent Ave. W., Winnipeg, MB R2C 3B2, Canada',
                'https://www.clubregent.com/entertainment',
                'R2C 3B2',
                '',
                'America/Winnipeg',
                'Winnipeg',
                'MB',
                'CA',
                49.8954192,
                -97.0441598,
                TRUE,
                'venue',
                'ticketmaster',
                'ticketmaster_comedy',
                'https://www.ticketmaster.com',
                'KovZpZAEee7A',
                '{}'::jsonb
            ),
            (
                'L''Olympia',
                '1004 Sainte-Catherine Street East, Montreal, QC H2L 2G2, Canada',
                'https://www.olympiamontreal.com/',
                'H2L 2G2',
                '',
                'America/Toronto',
                'Montreal',
                'QC',
                'CA',
                45.51701,
                -73.556874,
                TRUE,
                'venue',
                'ticketmaster',
                'ticketmaster_comedy',
                'https://www.ticketmaster.com',
                'KovZpa3Dre',
                '{}'::jsonb
            ),
            (
                'Leicester Square Theatre',
                '6 Leicester Place, London WC2H 7BX, United Kingdom',
                'https://www.leicestersquaretheatre.com/',
                'WC2H 7BX',
                '',
                'Europe/London',
                'London',
                '',
                'GB',
                51.511349,
                -0.130111,
                TRUE,
                'venue',
                'ticketmaster',
                'ticketmaster_comedy',
                'https://www.ticketmaster.com',
                'KovZ9177BEf',
                '{}'::jsonb
            ),
            (
                'Laugh Shop Calgary',
                '5940 Blackfoot Trail SE, Calgary, AB T2H 2B5, Canada',
                'https://laughshopcalgary.com',
                'T2H 2B5',
                '',
                'America/Edmonton',
                'Calgary',
                'AB',
                'CA',
                NULL::double precision,
                NULL::double precision,
                TRUE,
                'club',
                'showpass',
                'showpass',
                'https://www.showpass.com/api/public/venues/the-laugh-shop-calgary/calendar/',
                NULL,
                '{}'::jsonb
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
        country,
        latitude,
        longitude,
        visible,
        club_type,
        platform,
        scraper_key,
        source_url,
        ticketmaster_id,
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
        latitude,
        longitude,
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
        nc.country,
        nc.latitude,
        nc.longitude,
        nc.visible,
        'active',
        nc.club_type
    FROM normalized_candidates nc
    WHERE NOT EXISTS (
        SELECT 1
        FROM clubs existing
        WHERE existing.name = nc.name
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
      OR lower(regexp_replace(split_part(existing.address, ',', 1), '[^a-zA-Z0-9]+', '', 'g')) = nc.street_key
),
target_clubs AS (
    SELECT
        COALESCE(ic.id, ptc.club_id) AS club_id,
        nc.platform,
        nc.scraper_key,
        nc.source_url,
        nc.ticketmaster_id,
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
    ticketmaster_id,
    priority,
    enabled,
    metadata
)
SELECT
    tc.club_id,
    tc.platform::"ScrapingPlatform",
    tc.scraper_key,
    tc.source_url,
    tc.ticketmaster_id,
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
AND NOT EXISTS (
    SELECT 1
    FROM scraping_sources ss
    WHERE ss.enabled = TRUE
      AND (
          (tc.ticketmaster_id IS NOT NULL AND ss.ticketmaster_id = tc.ticketmaster_id)
          OR (tc.ticketmaster_id IS NULL AND ss.source_url = tc.source_url)
      )
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET
    scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    ticketmaster_id = EXCLUDED.ticketmaster_id,
    enabled = TRUE,
    metadata = EXCLUDED.metadata,
    updated_at = NOW()
WHERE scraping_sources.enabled = FALSE;
