-- TASK-3251: Correct Lesher Center from dead ShoWare host to Spektrix Link.
--
-- The TASK-3189 post-merge verifier proved lesherartscenter.showare.com does
-- not resolve in GHA. The public Lesher purchase app is Spektrix Link and its
-- eventsView.json catalog exposes a reliable Comedy and Improv genre.

UPDATE scraping_sources
   SET platform = 'custom'::"ScrapingPlatform",
       scraper_key = 'lesher_center',
       source_url = 'https://app.spektrix-link.com/clients/lesherartscenter/eventsView.json',
       enabled = TRUE,
       metadata = jsonb_build_object(
           'include_genres', jsonb_build_array('Comedy and Improv')
       ),
       updated_at = NOW()
 WHERE id = 6868
   AND club_id = 11099;
