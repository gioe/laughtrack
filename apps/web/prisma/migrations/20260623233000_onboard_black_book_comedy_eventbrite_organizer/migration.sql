-- Onboard Black Book Comedy (Bay Area, CA) as an Eventbrite organizer-mode
-- production_company -- TASK-3222.
--
-- TASK-3222 discovery targeted "The Dragon Dive Bar and Burgers" (3491 Clayton
-- Rd, Concord, CA 94519; Google place_id ChIJ7eN-__5hhYARRkAOTNJLUAw,
-- primary_type=bar). Investigation found that the venue's stand-up comedy is not
-- self-published by the bar -- it is produced by the roving comedy outfit
-- "Black Book Comedy" (blackbookcomedy.com, formerly Bay Area Comics), which
-- sells every show through a single Eventbrite organizer:
--   blackbookcomedy -- organizer id 18359324921
--   https://www.eventbrite.com/o/blackbookcomedy-18359324921
-- The organizer's own tagline is "Quality comedy entertainment all over the
-- bay!", and its upcoming feed runs at MANY rotating Bay Area rooms -- e.g.
-- The Dragon (Concord), Luigi's Deli & Market (Martinez), Martinez Event Center,
-- Bambino's (Vallejo). Onboarding The Dragon as a single fixed club + Eventbrite
-- venue source would (a) mis-attribute every Black Book show across the bay to
-- one Concord bar, and (b) silently yield 0 shows, because the /venues/{id}
-- endpoint returns HTTP 200 + an empty list for venues the API token does not own
-- (convention #192), defeating the venue->organizer fallback.
--
-- Resolution: producer, not venue. Modeled as a no-mapping Eventbrite
-- organizer-mode production company (the TASK-2108 Riot/Backdoor/Comet pattern,
-- mirrored by TASK-3214 Best Medicine Comedy and TASK-3178 The Spotlight Comedy).
-- ScrapingService synthesizes an in-memory organizer proxy from
-- production_companies.scraping_url, EventbriteScraper organizer mode groups
-- events by their own per-event venue, and ClubHandler.upsert_for_eventbrite_venue
-- routes each show to the correct auto-created per-venue club -- so The Dragon
-- (Concord) surfaces as one of those auto-created, browsable per-venue clubs,
-- alongside Luigi's, the Martinez Event Center, etc.
--
-- visible=TRUE here means SCRAPE-ENABLED (convention #218): ProductionCompany
-- Handler.get_all_production_companies() only loads visible production companies,
-- so an organizer-mode producer must be visible=TRUE to be scraped at all
-- (matching the working TASK-2108 Riot/Backdoor/Comet rows; the visible=FALSE
-- rows like Milwaukee Comedy are intentionally disabled). show_name_keywords is
-- empty: the organizer feed is a curated comedy producer's own listings
-- ("... Standup Comedy Show", "Martinez Comedy Fest", "The Dragon - Standup
-- comedy show"), so no title filter is needed -- The Dragon's separate karaoke
-- nights are not part of Black Book's Eventbrite feed.
--
-- NOTE on the lookalike organizers (kept distinct on purpose):
--   * "BlackBook Comedy | Martinez, CA" (eventbrite organizer 81607268923) is a
--     separate organizer profile; the roving 18359324921 org is the one that
--     lists The Dragon and the broader bay feed.
--   * TASK-3191 onboarded "Martinez Campbell Theater" via the unrelated
--     "Contra Costa Comedy" organizer (10954147007) -- different producer.

INSERT INTO production_companies (
    name,
    slug,
    website,
    scraping_url,
    visible,
    show_name_keywords
)
VALUES
    (
        'Black Book Comedy',
        'black-book-comedy-eventbrite-organizer',
        'https://blackbookcomedy.com/',
        'https://www.eventbrite.com/o/blackbookcomedy-18359324921',
        TRUE,
        ARRAY[]::text[]
    )
ON CONFLICT (name) DO UPDATE
SET slug = EXCLUDED.slug,
    website = EXCLUDED.website,
    scraping_url = EXCLUDED.scraping_url,
    visible = TRUE,
    show_name_keywords = EXCLUDED.show_name_keywords;

-- Organizer-mode rows must have no production_company_venues mappings: a mapped
-- production company uses the first mapped venue as a proxy, retaining that
-- venue's single-venue eventbrite_id and defeating organizer mode.
DELETE FROM production_company_venues AS pcv
USING production_companies AS pc
WHERE pc.id = pcv.production_company_id
  AND pc.slug = 'black-book-comedy-eventbrite-organizer';
