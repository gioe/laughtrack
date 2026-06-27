-- Onboard Teatro Trail / Sala Catarsis (Miami, FL) — TASK-3349,
-- objective #11 discover-comedy-venues near Miami 33130 / Fort Lauderdale 33301.
--
-- Spanish-language performing-arts theater that programs a heavy rotating slate
-- of Spanish stand-up. Its site (teatrotrail.com) and both halls — "Teatro Trail"
-- and "Sala Catarsis" (the operator's second room next door, 3717 SW 8th St) —
-- ticket through ONE OvationTix client (ci.ovationtix.com/36022), so a single
-- source covers both halls; all shows attach to this one club.
--
-- Handled by the existing `ovationtix` scraper. source_url is the OvationTix
-- SERIES view (web.ovationtix.com/trs/series/36022), which lists every upcoming
-- production on one static page (vs the /cal/ month view); the scraper extracts
-- production IDs and queries the OvationTix REST API per production.
--
-- MIXED-USE venue: alongside stand-up the calendar carries plays, an intimate
-- concert, a children's puppet show, and a graduation ceremony. metadata
-- comedy_filter=true scopes the source to comedy. Because these bookings are
-- Spanish and carry no English comedy keyword, TASK-3349 also taught the shared
-- is_comedy_event allowlist the Spanish terms comedia / comediante / humorista /
-- monólogo so the comedy bookings survive the filter while the non-comedy
-- programming is dropped.
--
-- Fixed VENUE (its own theater) -> visible=true. OvationTix performances carry a
-- wall-clock start; timezone America/New_York.
--
-- Verification: validated end-to-end against the LIVE OvationTix client 36022 —
-- 9 comedy productions kept (Kabeto, Alejandra Azcárate, Pedro González, Gaby
-- Alicea, Francisco Ramos, Piter Albeiro, Gonzalo Mihail, Juan Pablo López, El
-- Intercambio) = 18 upcoming shows persisted; 9 non-comedy productions (Fresa y
-- Chocolate, La Cucarachita Martina, Daymé Arocena concierto, White Coat
-- Ceremony, Oficialmente Gay 4, Andrés Vernazza, Nena's Show, Claudia Valdés,
-- Strings for Change) correctly filtered out.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Teatro Trail',
       '3715 SW 8th St',
       'https://www.teatrotrail.com',
       'Miami', 'FL', '33134',
       'America/New_York', 'US', 'club',
       'ChIJQ6Rv3HS32YgR2RpqAp7OKVs',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Teatro Trail'
     OR google_place_id = 'ChIJQ6Rv3HS32YgR2RpqAp7OKVs'
);

-- 2. The ovationtix scraping source. ovationtix_id (36022) is the column the
-- scraper reads for the client ID; source_url is the series-view discovery page.
-- metadata comedy_filter=true scopes this mixed-use venue to comedy. Locate the
-- club by name OR google_place_id for idempotency parity with the guard above.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, ovationtix_id, priority, enabled, metadata)
SELECT c.id, 'ovationtix', 'ovationtix',
       'https://web.ovationtix.com/trs/series/36022',
       '36022',
       0, true, '{"comedy_filter": true}'::jsonb
FROM clubs c
WHERE (c.name = 'Teatro Trail' OR c.google_place_id = 'ChIJQ6Rv3HS32YgR2RpqAp7OKVs')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'ovationtix'
  );
