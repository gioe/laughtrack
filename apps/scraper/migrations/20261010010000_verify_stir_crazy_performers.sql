-- TASK-4148: verified official detail descriptions identify acts that boilerplate
-- Person JSON-LD omits or replaces with the program title. Restrict corrections
-- to exact event paths AND local dates so reused slugs cannot inherit old casts.
UPDATE scraping_sources
SET metadata = COALESCE(metadata, '{}'::jsonb) ||
    '{"performer_overrides":{
      "/tons-of-fun-9822#2026-11-01":["Dan Diego","Gabriel Olivares","Pete Perez","Liz Gaynor","Greg Frieler","Mike James"],
      "/life-of-nurmi-721#2026-10-17":["Kirk Nurmi","Ashley Rose","Mike Dapper","Chris Bennett"],
      "/comedy-hypnosis-show-5393#2026-11-22":["Johnathan Mark Smith","Mike Harris"],
      "/jay-penn-748#2026-11-27":["Jay Penn"],
      "/jay-penn-748#2026-11-28":["Jay Penn"]
    }}'::jsonb,
    updated_at = NOW()
WHERE club_id = 17393 AND platform = 'custom'::"ScrapingPlatform"
  AND priority = 0 AND scraper_key = 'stir_crazy';
