-- TASK-3029: Backfill verified city/state components for visible venue clubs.
--
-- The address audit after TASK-3027 left two classes of visible rows:
--   1. Real venue clubs with city/state missing after Google Places address
--      backfill or older address parsing gaps.
--   2. Non-venue aggregate rows that should not receive fake city values.
--
-- This migration keeps the non-venue rows classified as non-venues and fills
-- only verified location components for actual venues.

CREATE TEMP TABLE club_city_state_component_backfill (
    club_id integer PRIMARY KEY,
    city text,
    state text NOT NULL,
    rationale text NOT NULL
) ON COMMIT DROP;

INSERT INTO club_city_state_component_backfill (club_id, city, state, rationale)
VALUES
    (13, 'Brooklyn', 'NY', 'parsed from verified address'),
    (20, 'New York', 'NY', 'parsed from verified address'),
    (50, 'New York', 'NY', 'parsed from verified address'),
    (58, 'Charlotte', 'NC', 'parsed from verified address'),
    (80, 'Providence', 'RI', 'parsed from verified address'),
    (81, 'Burlington', 'VT', 'parsed from verified address'),
    (83, 'North Charleston', 'SC', 'parsed from verified address'),
    (101, 'Newport News', 'VA', 'parsed from verified address'),
    (106, 'Seattle', 'WA', 'parsed from verified address'),
    (120, 'Chandler', 'AZ', 'parsed from verified address'),
    (123, 'Louisville', 'KY', 'parsed from verified address'),
    (217, 'East Providence', 'RI', 'parsed from Google Places-backed address'),
    (288, 'Wilmington', 'NC', 'parsed from Google Places-backed address'),
    (327, 'New York', 'NY', 'parsed from Google Places-backed address'),
    (409, 'Washington', 'DC', 'parsed from Google Places-backed address'),
    (447, 'Alameda', 'CA', 'parsed from Google Places-backed address'),
    (461, 'New York', 'NY', 'parsed from Google Places-backed address'),
    (469, 'West Nyack', 'NY', 'parsed from Google Places-backed address'),
    (475, 'Santa Monica', 'CA', 'parsed from Google Places-backed address'),
    (476, 'Long Beach', 'CA', 'parsed from Google Places-backed address'),
    (479, 'Alsip', 'IL', 'parsed from Google Places-backed address'),
    (481, 'Bellmore', 'NY', 'parsed from Google Places-backed address'),
    (482, 'Bohemia', 'NY', 'parsed from Google Places-backed address'),
    (519, 'Peoria', 'IL', 'parsed from Google Places-backed address'),
    (524, 'Gaithersburg', 'MD', 'parsed from Google Places-backed address'),
    (542, 'Marietta', 'GA', 'parsed from Google Places-backed address'),
    (548, 'Massillon', 'OH', 'parsed from Google Places-backed address'),
    (551, 'Manteca', 'CA', 'parsed from Google Places-backed address'),
    (554, 'Phoenix', 'AZ', 'parsed from Google Places-backed address'),
    (562, 'Hickory', 'NC', 'parsed from Google Places-backed address'),
    (565, 'Baltimore', 'MD', 'parsed from Google Places-backed address'),
    (572, 'Chicopee', 'MA', 'parsed from Google Places-backed address'),
    (579, 'San Francisco', 'CA', 'parsed from Google Places-backed address'),
    (592, 'Forest Park', 'IL', 'parsed from Google Places-backed address'),
    (600, 'New Rochelle', 'NY', 'parsed from Google Places-backed address'),
    (611, 'New Orleans', 'LA', 'parsed from Google Places-backed address'),
    (613, 'Hoboken', 'NJ', 'parsed from Google Places-backed address'),
    (622, 'Cleveland', 'OH', 'parsed from Google Places-backed address'),
    (628, 'New Hope', 'PA', 'parsed from Google Places-backed address'),
    (629, 'Lawrence', 'KS', 'parsed from Google Places-backed address'),
    (632, 'Springfield', 'MO', 'parsed from Google Places-backed address'),
    (633, 'Hoover', 'AL', 'parsed from Google Places-backed address'),
    (634, 'Detroit', 'MI', 'parsed from Google Places-backed address'),
    (638, 'New Cumberland', 'PA', 'parsed from Google Places-backed address'),
    (855, 'Jersey City', 'NJ', 'parsed from Google Places-backed address'),
    (1061, 'Madrid', 'Community of Madrid', 'verified from venue address'),
    (1347, 'Brooklyn', 'NY', 'parsed from Google Places-backed address'),
    (1348, 'Akron', 'OH', 'parsed from Google Places-backed address');

UPDATE clubs c
SET city = b.city,
    state = b.state,
    country = COALESCE(c.country, CASE WHEN b.state = 'Community of Madrid' THEN 'Spain' ELSE 'US' END),
    description = CASE
        WHEN c.description LIKE '%Updated by TASK-3029:%' THEN c.description
        ELSE concat_ws(
            E'\n\n',
            NULLIF(c.description, ''),
            'Updated by TASK-3029: city/state components ' || b.rationale
        )
    END
FROM club_city_state_component_backfill b
WHERE c.id = b.club_id
  AND (
      c.city IS DISTINCT FROM b.city
      OR c.state IS DISTINCT FROM b.state
      OR c.country IS NULL
  );

UPDATE clubs
SET club_type = 'producer',
    description = CASE
        WHEN description LIKE '%Updated by TASK-3029:%' THEN description
        ELSE concat_ws(
            E'\n\n',
            NULLIF(description, ''),
            'Updated by TASK-3029: classified as a producer aggregate, not a single venue; city intentionally remains blank.'
        )
    END
WHERE id = 539
  AND club_type IS DISTINCT FROM 'producer';

DO $$
DECLARE
    affected_count integer;
    malformed_count integer;
    producer_type text;
    festival_type text;
BEGIN
    SELECT count(*) INTO affected_count
    FROM club_city_state_component_backfill b
    JOIN clubs c ON c.id = b.club_id
    WHERE c.city IS DISTINCT FROM b.city
       OR c.state IS DISTINCT FROM b.state;

    IF affected_count <> 0 THEN
        RAISE EXCEPTION 'TASK-3029 left % city/state venue backfills unapplied', affected_count;
    END IF;

    SELECT count(*) INTO malformed_count
    FROM clubs
    WHERE visible = TRUE
      AND club_type = 'club'
      AND (
          city IS NULL
          OR btrim(city) = ''
          OR state IS NULL
          OR btrim(state) = ''
          OR city ~ '^[0-9]'
      );

    IF malformed_count <> 0 THEN
        RAISE EXCEPTION 'TASK-3029 left % visible venue clubs with blank or malformed city/state', malformed_count;
    END IF;

    SELECT club_type INTO producer_type FROM clubs WHERE id = 539;
    IF producer_type IS DISTINCT FROM 'producer' THEN
        RAISE EXCEPTION 'TASK-3029 did not classify Kricket Comedy as a producer aggregate';
    END IF;

    SELECT club_type INTO festival_type FROM clubs WHERE id = 573;
    IF festival_type IS DISTINCT FROM 'festival' THEN
        RAISE EXCEPTION 'TASK-3029 expected Big Pine Comedy Festival to remain club_type=festival';
    END IF;
END $$;
