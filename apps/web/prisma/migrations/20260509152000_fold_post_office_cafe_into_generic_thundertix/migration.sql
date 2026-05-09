-- TASK-2070: Fold Post Office Cafe & Cabaret (club_id=223) onto GenericThunderTixScraper.
--
-- The bespoke PostOfficeCafeScraper / PostOfficeCafePerformance / PostOfficeCafePageData
-- trio has been replaced by GenericThunderTixScraper (key='thundertix') which
-- reads its config from scraping_sources. This migration repoints the existing
-- row from platform=custom + scraper_key='post_office_cafe' to the generic
-- platform. Post Office Cafe has no venue-specific title-skip rules (the only
-- ThunderTix filter the venue scraper applied was the engine-level
-- publicly_available check, which lives on the generic scraper too), so
-- metadata.title_skip_prefixes is intentionally not set.
UPDATE scraping_sources
SET
    platform = 'thundertix'::"ScrapingPlatform",
    scraper_key = 'thundertix',
    source_url = 'https://postofficecafecabaret.thundertix.com',
    updated_at = CURRENT_TIMESTAMP
-- Match enabled and disabled rows alike: a disabled row left behind would still
-- point at the deleted scraper_key='post_office_cafe' code path, so it would
-- silently become an unknown-scraper landmine if ever re-enabled.
WHERE club_id = 223
  AND platform = 'custom'::"ScrapingPlatform"
  AND scraper_key = 'post_office_cafe';
