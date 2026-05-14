-- Create the City Winery chain and link verified City Winery venues.
--
-- City Winery uses one shared brand and event API across locations, but each
-- club still needs per-location scraping_sources.metadata.location, so this
-- migration only establishes chain identity. Per-club source rows remain the
-- runtime scraper configuration.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs
        WHERE id = 2420
          AND name = 'City Winery - New York City'
          AND city = 'New York'
          AND state = 'NY'
          AND visible = TRUE
          AND status = 'active'
    ) THEN
        RAISE EXCEPTION 'Cannot link City Winery chain: NYC club 2420 is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM clubs
        WHERE id = 2423
          AND name = 'City Winery Boston'
          AND city = 'Boston'
          AND state = 'MA'
          AND visible = TRUE
          AND status = 'active'
    ) THEN
        RAISE EXCEPTION 'Cannot link City Winery chain: Boston club 2423 is missing or changed';
    END IF;
END $$;

WITH chain_row AS (
    INSERT INTO chains (
        name,
        slug,
        website
    )
    VALUES (
        'City Winery',
        'city-winery',
        'https://citywinery.com'
    )
    ON CONFLICT (slug) DO UPDATE
    SET name = EXCLUDED.name,
        website = EXCLUDED.website
    RETURNING id
)
UPDATE clubs
SET chain_id = (SELECT id FROM chain_row)
WHERE id IN (2420, 2423)
  AND (
      (id = 2420 AND name = 'City Winery - New York City' AND city = 'New York' AND state = 'NY')
      OR (id = 2423 AND name = 'City Winery Boston' AND city = 'Boston' AND state = 'MA')
  );
