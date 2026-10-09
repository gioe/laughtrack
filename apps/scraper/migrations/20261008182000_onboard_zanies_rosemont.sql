-- TASK-4144: Rosemont's homepage advertises only the current month's teaser.
-- Its RHP month calendar exposes 119 upcoming performances through May 2027
-- (verified 2026-10-08), compared with three Live Nation performances.
-- Keep the existing venue and Live Nation fallback; do not create a new club.
UPDATE clubs
SET website = 'https://rosemont.zanies.com/',
    chain_id = COALESCE(chain_id, (SELECT id FROM chains WHERE slug = 'zanies'))
WHERE id = 4648;

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, priority, enabled, metadata
)
SELECT id, 'custom'::"ScrapingPlatform", 'zanies',
       'https://rosemont.zanies.com/calendar/?view=month', 0, TRUE,
       '{"task_4144":"Direct full RHP month calendar; Live Nation remains priority-1 fallback"}'::jsonb
FROM clubs WHERE id = 4648
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = COALESCE(scraping_sources.metadata, '{}'::jsonb) || EXCLUDED.metadata,
    updated_at = NOW();
