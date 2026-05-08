-- Delete orphan duplicate Laugh Factory club rows (TASK-2043).
--
-- Two zero-show eventbrite-only rows duplicate the canonical chain entries:
--   id 2273 'Laugh Factory - Hollywood' (LA, 0 shows) -> dupe of id 160 'Laugh Factory Hollywood' (252 shows)
--   id 2277 'Laugh Factory'             (SD, 0 shows) -> dupe of id 170 'Laugh Factory San Diego'  ( 75 shows)
--
-- Pre-flight audit (2026-05-08): both rows have visible=false, total_shows=0,
-- and zero references in shows / tagged_clubs / email_subscriptions /
-- processed_emails / production_company_venues. Each carries one disabled
-- scraping_sources row (1272 / 1276, both eventbrite, enabled=false,
-- source_url='https://www.eventbrite.com'); ON DELETE CASCADE drops them
-- with the parent club. The canonical rows (160, 170) carry their own
-- enabled eventbrite sources (499, 365), so deleting these stubs does not
-- lose any live scrape configuration.
--
-- After deploy, the seven canonical Laugh Factory rows (160, 168, 169, 170,
-- 171, 172, 173) match the seven venues listed on https://www.laughfactory.com.
-- Mirror of TASK-2042 (Funny Bone orphans 310, 1037).

DELETE FROM clubs
WHERE id = 2273
  AND name = 'Laugh Factory - Hollywood'
  AND total_shows = 0
  AND visible = false;

DELETE FROM clubs
WHERE id = 2277
  AND name = 'Laugh Factory'
  AND total_shows = 0
  AND visible = false;
