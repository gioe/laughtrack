-- TASK-714: Recover seatengine_id for 39 seatengine_classic clubs nulled by TASK-711.
--
-- Background: TASK-711 nulled seatengine_id for 39 seatengine_classic clubs because
-- no matching API venue was found in the 1–700 enumeration. This migration restores
-- numeric IDs extracted from each venue's own HTML page via SeatEngine CDN URLs:
--   files.seatengine.com/styles/logos/{ID}/...
--   files.seatengine.com/styles/header_images/{ID}/...
--
-- These IDs are the venues' original SeatEngine asset/file IDs from the classic
-- platform. The current new-platform API may show different venues at these IDs
-- (IDs appear to be recycled as venues migrate/deactivate), so they do NOT pass
-- the API name-match audit. They are stored as historical reference only.
--
-- seatengine_classic uses scraping_url at runtime, NOT seatengine_id, so these
-- values have no scraping impact. See TASK-713 for documentation of this.
--
-- Applied via: make run-script SCRIPT=scripts/core/recover_seatengine_classic_ids.py
-- All 39 clubs matched (0 unmatched). Source: CDN URL extraction from scraping_url HTML.

UPDATE clubs SET seatengine_id = '443' WHERE id = 42;   -- McGuire's Comedy Club
UPDATE clubs SET seatengine_id = '442' WHERE id = 43;   -- Brokerage Comedy Club
UPDATE clubs SET seatengine_id = '441' WHERE id = 44;   -- Governors' Comedy Club
UPDATE clubs SET seatengine_id = '310' WHERE id = 45;   -- Stress Factory
UPDATE clubs SET seatengine_id = '311' WHERE id = 46;   -- Stress Factory Bridgeport
UPDATE clubs SET seatengine_id = '466' WHERE id = 47;   -- Comedy In Harlem
UPDATE clubs SET seatengine_id = '420' WHERE id = 53;   -- Dania Improv
UPDATE clubs SET seatengine_id = '448' WHERE id = 57;   -- The Comedy Zone Greensboro
UPDATE clubs SET seatengine_id = '402' WHERE id = 58;   -- The Comedy Zone - Charlotte
UPDATE clubs SET seatengine_id = '453' WHERE id = 59;   -- Comedy Zone Jacksonville
UPDATE clubs SET seatengine_id = '504' WHERE id = 60;   -- The Comedy Zone - Cherokee
UPDATE clubs SET seatengine_id = '425' WHERE id = 67;   -- The Comedy Catch
UPDATE clubs SET seatengine_id = '338' WHERE id = 69;   -- The Comedy Club of Kansas City
UPDATE clubs SET seatengine_id = '401' WHERE id = 70;   -- The Comedy Fort
UPDATE clubs SET seatengine_id = '298' WHERE id = 71;   -- The Comedy Loft of DC
UPDATE clubs SET seatengine_id = '389' WHERE id = 72;   -- The Comedy Vault
UPDATE clubs SET seatengine_id = '392' WHERE id = 75;   -- The Dojo of Comedy
UPDATE clubs SET seatengine_id = '487' WHERE id = 77;   -- The Well Comedy Club
UPDATE clubs SET seatengine_id = '368' WHERE id = 79;   -- Underground Comedy
UPDATE clubs SET seatengine_id = '519' WHERE id = 83;   -- Wit's End Comedy Lounge
UPDATE clubs SET seatengine_id = '324' WHERE id = 88;   -- Barrel Room Portland
UPDATE clubs SET seatengine_id = '359' WHERE id = 90;   -- Bricktown Comedy Club
UPDATE clubs SET seatengine_id = '561' WHERE id = 92;   -- Bricky's Comedy Club
UPDATE clubs SET seatengine_id = '588' WHERE id = 94;   -- Capitol Hill Comedy Bar (scraping_url redirects to emeraldcitycomedy.com → same venue ID)
UPDATE clubs SET seatengine_id = '564' WHERE id = 95;   -- Coastal Creative
UPDATE clubs SET seatengine_id = '484' WHERE id = 97;   -- Comedy Cabin
UPDATE clubs SET seatengine_id = '328' WHERE id = 104;  -- Desert Ridge Improv
UPDATE clubs SET seatengine_id = '588' WHERE id = 106;  -- Emerald City Comedy Club
UPDATE clubs SET seatengine_id = '132' WHERE id = 108;  -- Helium & Elements Restaurant - St. Louis
UPDATE clubs SET seatengine_id = '537' WHERE id = 114;  -- Laugh Camp Comedy Club
UPDATE clubs SET seatengine_id = '460' WHERE id = 116;  -- Loonees Comedy Corner
UPDATE clubs SET seatengine_id = '414' WHERE id = 117;  -- Louisville Comedy Club
UPDATE clubs SET seatengine_id = '301' WHERE id = 118;  -- Magoobys Joke House
UPDATE clubs SET seatengine_id = '419' WHERE id = 123;  -- Planet Of The Tapes (planetofthetapes.seatengine.com)
UPDATE clubs SET seatengine_id = '483' WHERE id = 124;  -- Rooster T. Feathers Comedy Club (rooster-t-feathers.seatengine-sites.com)
UPDATE clubs SET seatengine_id = '587' WHERE id = 127;  -- Snappers Palm Harbor
UPDATE clubs SET seatengine_id = '336' WHERE id = 129;  -- StandUpLive Phoenix
UPDATE clubs SET seatengine_id = '601' WHERE id = 130;  -- Stress Factory - Valley Forge
UPDATE clubs SET seatengine_id = '530' WHERE id = 134;  -- Helium Comedy Club - Atlanta
