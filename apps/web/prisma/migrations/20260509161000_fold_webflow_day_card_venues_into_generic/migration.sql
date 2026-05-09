-- [TASK-2086] Fold The Comic Strip Edmonton + House of Comedy BC onto the
-- generic tixr_webflow_day_card scraper.
--
-- The bespoke ComicStripEdmontonScraper / HouseOfComedyBcScraper classes
-- were thin wrappers around the shared WebflowDayCardExtractor; the only
-- per-venue input was a Tixr group URL fragment used to filter foreign
-- cards. The new TixrWebflowDayCardScraper (key='tixr_webflow_day_card')
-- reads source_url from scraping_sources and tixr_group_fragment from
-- scraping_sources.metadata, so the wrappers can be deleted and these two
-- venues now route through the generic key.
--
-- HAHA Comedy Club is intentionally NOT migrated: its calendar page is
-- JSON-LD plus visible time markup, not a.day-card, so the day-card
-- extractor would not match. It keeps its custom scraper (key='haha_comedy_club').

UPDATE scraping_sources ss
SET
    scraper_key = 'tixr_webflow_day_card',
    metadata = COALESCE(ss.metadata, '{}'::jsonb)
        || jsonb_build_object(
            'tixr_group_fragment',
            'tixr.com/groups/comicstripedmonton/events/'
        ),
    updated_at = NOW()
FROM clubs c
WHERE ss.club_id = c.id
  AND c.name = 'The Comic Strip West Edmonton Mall'
  AND ss.platform = 'custom'::"ScrapingPlatform"
  AND ss.scraper_key = 'comic_strip_edmonton';

UPDATE scraping_sources ss
SET
    scraper_key = 'tixr_webflow_day_card',
    metadata = COALESCE(ss.metadata, '{}'::jsonb)
        || jsonb_build_object(
            'tixr_group_fragment',
            'tixr.com/groups/comicstripbc/events/'
        ),
    updated_at = NOW()
FROM clubs c
WHERE ss.club_id = c.id
  AND c.name = 'House of Comedy British Columbia'
  AND ss.platform = 'custom'::"ScrapingPlatform"
  AND ss.scraper_key = 'house_of_comedy_bc';
