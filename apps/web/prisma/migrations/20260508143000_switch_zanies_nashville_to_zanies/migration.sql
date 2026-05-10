-- Switch Zanies Nashville from the generic Etix venue page to the public
-- Zanies-owned site. The public site exposes the complete event list and links
-- to Etix only for final ticket checkout.

UPDATE scraping_sources
SET enabled = FALSE,
    updated_at = NOW(),
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_2017_disposition',
        'disabled_etix_primary_after_zanies_owned_page_supported'
    )
WHERE club_id = 1029
  AND platform = 'etix'::"ScrapingPlatform";

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    enabled,
    priority,
    metadata,
    created_at,
    updated_at
)
SELECT
    1029,
    'custom'::"ScrapingPlatform",
    'zanies',
    'https://nashville.zanies.com/',
    TRUE,
    0,
    jsonb_build_object(
        'task_2017_onboard',
        jsonb_build_object(
            'rationale',
            'Use the public Zanies Nashville site as primary; Etix remains only the ticket checkout link exposed by event pages.'
        )
    ),
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1
    FROM scraping_sources
    WHERE club_id = 1029
      AND platform = 'custom'::"ScrapingPlatform"
      AND priority = 0
);

UPDATE scraping_sources
SET scraper_key = 'zanies',
    source_url = 'https://nashville.zanies.com/',
    enabled = TRUE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_2017_onboard',
        jsonb_build_object(
            'rationale',
            'Use the public Zanies Nashville site as primary; Etix remains only the ticket checkout link exposed by event pages.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 1029
  AND platform = 'custom'::"ScrapingPlatform"
  AND priority = 0;

UPDATE clubs
SET website = 'https://nashville.zanies.com'
WHERE id = 1029;
