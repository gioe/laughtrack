-- TASK-2070: Fold The Annoyance Theatre (club_id=183) onto GenericThunderTixScraper.
--
-- The bespoke AnnoyanceTheatreScraper / AnnoyancePerformance / AnnoyancePageData
-- trio has been replaced by GenericThunderTixScraper (key='thundertix') which
-- reads its config from scraping_sources. This migration repoints the existing
-- row from platform=custom + scraper_key='annoyance' to the generic platform
-- and stores the Annoyance-specific class/training-center skip rules in
-- metadata.title_skip_prefixes (CSV) so the generic scraper preserves the
-- exact filter behavior from the deleted venue subclass.
UPDATE scraping_sources
SET
    platform = 'thundertix'::"ScrapingPlatform",
    scraper_key = 'thundertix',
    source_url = 'https://theannoyance.thundertix.com',
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'title_skip_prefixes', 'CLASS:,TRAINING CENTER:'
    ),
    updated_at = CURRENT_TIMESTAMP
-- Match enabled and disabled rows alike: a disabled row left behind would still
-- point at the deleted scraper_key='annoyance' code path, so it would silently
-- become an unknown-scraper landmine if ever re-enabled.
WHERE club_id = 183
  AND platform = 'custom'::"ScrapingPlatform"
  AND scraper_key = 'annoyance';
