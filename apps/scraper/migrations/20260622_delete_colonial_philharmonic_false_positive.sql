-- TASK-3168: Remove Colonial OvationTix false positive from verification scrape.
--
-- The initial TASK-3168 live scrape kept this silent-film/live-score production
-- because its description includes "physical comedy". After adding Colonial's
-- exclude_title_patterns, the corrected scraper no longer emits it. Delete the
-- exact show row created by the verification scrape; dependent tickets/tags
-- cascade from shows per schema.prisma.

DELETE FROM shows
 WHERE club_id = (
     SELECT id
       FROM clubs
      WHERE google_place_id = 'ChIJ453HtoBz4YkRCrrHlZU2Eq8'
      LIMIT 1
 )
   AND name = 'New England Philharmonic Chamber Ensemble'
   AND show_page_url = 'https://ci.ovationtix.com/36697/production/1278413?performanceId=11819809';
