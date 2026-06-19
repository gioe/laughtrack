-- TASK-3017: repair clubs whose original tour_dates discovery address parsed
-- an event-year fragment as the city, while preserving their valid
-- Ticketmaster sources and shows.
--
-- Live disposition:
--   preserve/update:
--     2950 Aztec Theatre                  '‘26 San Antonio' -> San Antonio, TX
--     2952 713 Music Hall                 '‘26 Houston'     -> Houston, TX
--     2953 Majestic Theatre               '‘26 Dallas'      -> Dallas, TX
--     2955 The Chicago Theatre            '‘26 Chicago'     -> Chicago, IL
--     2956 Emerald Queen Casino           '‘26 Tacoma'      -> Tacoma, WA
--     2959 Elsinore Theatre               '‘26 Salem'       -> Salem, OR
--
--   already retired by TASK-3016:
--     2949 Youtube Theater                closed/hidden, zero shows/sources
--     2957 Neal S. Blaisdell Concert Hall closed/hidden, zero shows/sources
--     2951 713 Music Hall May 17 '26 Dallas, TX Majestic Theatre deleted
--
-- Root cause: the removed tour_dates discovery path called
-- parse_city_state_from_address() with bare tour-list fragments such as
-- "‘26 Chicago, IL". The parser accepted the penultimate comma segment as a
-- city whenever the final segment was a valid state. TASK-3017 adds parser
-- validation so digit-bearing date fragments no longer become city values.

CREATE TEMP TABLE malformed_tour_date_city_repairs (
    club_id integer PRIMARY KEY,
    expected_name text NOT NULL,
    expected_city text NOT NULL,
    fixed_address text NOT NULL,
    fixed_city text NOT NULL,
    fixed_state text NOT NULL
) ON COMMIT DROP;

INSERT INTO malformed_tour_date_city_repairs (
    club_id,
    expected_name,
    expected_city,
    fixed_address,
    fixed_city,
    fixed_state
)
VALUES
    (2950, 'Aztec Theatre', '‘26 San Antonio', 'San Antonio, TX', 'San Antonio', 'TX'),
    (2952, '713 Music Hall', '‘26 Houston', 'Houston, TX', 'Houston', 'TX'),
    (2953, 'Majestic Theatre', '‘26 Dallas', 'Dallas, TX', 'Dallas', 'TX'),
    (2955, 'The Chicago Theatre', '‘26 Chicago', 'Chicago, IL', 'Chicago', 'IL'),
    (2956, 'Emerald Queen Casino', '‘26 Tacoma', 'Tacoma, WA', 'Tacoma', 'WA'),
    (2959, 'Elsinore Theatre', '‘26 Salem', 'Salem, OR', 'Salem', 'OR');

DO $$
DECLARE
    missing_count integer;
    unsafe_count integer;
BEGIN
    SELECT count(*) INTO missing_count
    FROM malformed_tour_date_city_repairs r
    LEFT JOIN clubs c
      ON c.id = r.club_id
     AND c.name = r.expected_name
     AND c.city = r.expected_city
     AND c.visible = TRUE
     AND c.status = 'active'
    WHERE c.id IS NULL;

    IF missing_count <> 0 THEN
        RAISE EXCEPTION 'TASK-3017 malformed city repair candidates are missing or changed: %', missing_count;
    END IF;

    SELECT count(*) INTO unsafe_count
    FROM malformed_tour_date_city_repairs r
    JOIN clubs c ON c.id = r.club_id
    WHERE NOT EXISTS (
        SELECT 1
        FROM scraping_sources ss
        WHERE ss.club_id = c.id
          AND ss.platform = 'ticketmaster'::"ScrapingPlatform"
          AND ss.enabled = TRUE
    )
    OR NOT EXISTS (
        SELECT 1
        FROM shows s
        WHERE s.club_id = c.id
    );

    IF unsafe_count <> 0 THEN
        RAISE EXCEPTION 'TASK-3017 repair candidates lost expected Ticketmaster source or shows: %', unsafe_count;
    END IF;
END $$;

UPDATE clubs c
SET
    address = r.fixed_address,
    city = r.fixed_city,
    state = r.fixed_state,
    description = trim(both E'\n' FROM concat_ws(
        E'\n',
        NULLIF(c.description, ''),
        'TASK-3017: corrected malformed tour_dates city/address fragment; valid Ticketmaster source and shows preserved.'
    ))
FROM malformed_tour_date_city_repairs r
WHERE c.id = r.club_id;

DO $$
DECLARE
    remaining_count integer;
BEGIN
    SELECT count(*) INTO remaining_count
    FROM clubs c
    WHERE c.visible = TRUE
      AND c.status = 'active'
      AND (
          c.city LIKE '‘%'
          OR c.city LIKE '’%'
          OR c.address LIKE '‘%'
          OR c.address LIKE '’%'
      )
      AND EXISTS (
          SELECT 1
          FROM scraping_sources ss
          WHERE ss.club_id = c.id
            AND ss.platform = 'tour_dates'::"ScrapingPlatform"
      );

    IF remaining_count <> 0 THEN
        RAISE EXCEPTION 'TASK-3017 malformed active tour_dates city rows remain: %', remaining_count;
    END IF;
END $$;
