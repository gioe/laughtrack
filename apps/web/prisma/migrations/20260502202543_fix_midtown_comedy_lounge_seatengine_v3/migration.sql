-- Fix Midtown Comedy Lounge (club 589): current public storefront is the
-- SeatEngine v3 seatengine.net domain. The older seatengine-sites.com URL
-- still serves static venue chrome but no events, and the duplicate classic
-- SeatEngine source adds an unnecessary zero-show fallback.

UPDATE clubs
SET website = 'https://v-364f13ff-86b9-479f-9720-bd191e285ac3.seatengine.net/'
WHERE id = 589
  AND name = 'Midtown Comedy Lounge';

UPDATE scraping_sources
SET source_url = 'https://v-364f13ff-86b9-479f-9720-bd191e285ac3.seatengine.net/',
    external_id = '364f13ff-86b9-479f-9720-bd191e285ac3',
    enabled = true
WHERE club_id = 589
  AND platform = 'seatengine_v3'::"ScrapingPlatform";

UPDATE scraping_sources
SET enabled = false
WHERE club_id = 589
  AND platform = 'seatengine'::"ScrapingPlatform"
  AND external_id = '569';
