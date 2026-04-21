-- [TASK-1693] Drop deprecated scraper configuration columns from clubs after
-- runtime reads and writes have been migrated to scraping_sources.

ALTER TABLE clubs
    DROP COLUMN IF EXISTS scraper,
    DROP COLUMN IF EXISTS scraping_url,
    DROP COLUMN IF EXISTS ticketmaster_id,
    DROP COLUMN IF EXISTS seatengine_id,
    DROP COLUMN IF EXISTS eventbrite_id,
    DROP COLUMN IF EXISTS ovationtix_client_id,
    DROP COLUMN IF EXISTS wix_comp_id,
    DROP COLUMN IF EXISTS wix_category_id,
    DROP COLUMN IF EXISTS squadup_user_id;
