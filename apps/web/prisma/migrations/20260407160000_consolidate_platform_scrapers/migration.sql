-- Add platform-specific ID columns for generic scrapers
ALTER TABLE "clubs" ADD COLUMN IF NOT EXISTS "ovationtix_client_id" TEXT;
ALTER TABLE "clubs" ADD COLUMN IF NOT EXISTS "wix_comp_id" TEXT;
ALTER TABLE "clubs" ADD COLUMN IF NOT EXISTS "wix_category_id" TEXT;
ALTER TABLE "clubs" ADD COLUMN IF NOT EXISTS "squadup_user_id" TEXT;

-- OvationTix venues → generic 'ovationtix' scraper
UPDATE "clubs" SET ovationtix_client_id = '35843', scraper = 'ovationtix'
WHERE scraper = 'comedy_at_the_carlson';

UPDATE "clubs" SET ovationtix_client_id = '36367', scraper = 'ovationtix'
WHERE scraper = 'four_day_weekend';

UPDATE "clubs" SET ovationtix_client_id = '35774', scraper = 'ovationtix',
  scraping_url = 'https://web.ovationtix.com/trs/cal/35774'
WHERE scraper = 'uncle_vinnies';

-- Wix Events venues → generic 'wix_events' scraper
UPDATE "clubs" SET wix_comp_id = 'comp-lzt5zlma',
  wix_category_id = '41b1dace-b9ba-49dd-a961-f48839c0fce0',
  scraper = 'wix_events'
WHERE scraper = 'bushwick';

UPDATE "clubs" SET wix_comp_id = 'comp-m4t1prev', scraper = 'wix_events'
WHERE scraper = 'nicks_comedy_stop';

UPDATE "clubs" SET wix_comp_id = 'comp-j9ny0yyr', scraper = 'wix_events'
WHERE scraper = 'red_room';

-- SquadUP venues → generic 'squadup' scraper
UPDATE "clubs" SET squadup_user_id = '7408591', scraper = 'squadup'
WHERE scraper = 'dynasty_typewriter';

UPDATE "clubs" SET squadup_user_id = '9086799', scraper = 'squadup'
WHERE scraper = 'sunset_strip';
