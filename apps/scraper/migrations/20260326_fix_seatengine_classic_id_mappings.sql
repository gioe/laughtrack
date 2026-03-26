-- TASK-711: Fix seatengine_classic seatengine_id mismatches
--
-- Background: seatengine_classic scrapes HTML from scraping_url and does NOT use
-- seatengine_id at runtime. The IDs stored were wrong (same +15-offset shuffle as
-- TASK-710 v1 clubs, plus many pointing to non-existent API IDs > 297).
--
-- Strategy:
--   A) 11 clubs with confirmed correct IDs found via API name + website match → UPDATE
--   B) 39 clubs with no correct ID found (API returns 404, or no name match in 1–700)
--      → SET seatengine_id = NULL (unused field for classic scraper; wrong value misleads future audits)
--
-- Confirmed fixes (A) — verified by GET /api/v1/venues/{id} name match + website URL:
--
-- club_id | DB name                              | old_id | new_id | evidence
--      64 | Tacoma Comedy Club                   |    157 |    158 | API: 'Tacoma Comedy Club' tacomacomedyclub.com
--      65 | The Caravan                          |    230 |    245 | API: 'The Caravan' thecaravan2017.com
--      66 | The Comedy Attic                     |    206 |    218 | API: 'The Comedy Attic' comedyattic.com
--      74 | The Comic Strip                      |    162 |    163 | API: 'The Comic Strip' elpasocomicstrip.com
--      81 | Vermont Comedy Club                  |    124 |    125 | API: 'Vermont Comedy Club' vtcomedy.com
--      87 | Bananas Comedy Club Renaissance Hotel|    282 |    297 | API: 'Bananas Comedy Club Renaissance Hotel' bananascomedyclub.com
--     102 | DC Improv                            |    275 |    290 | API: 'DC Improv' dcimprov.com
--     107 | Fort Wayne Comedy Club @ 469         |    270 |    285 | API: 'Fort Wayne Comedy Club @ 469' fortwaynecomedyclub.com
--     122 | Off The Hook Comedy Club             |    192 |    204 | API: 'Off The Hook Comedy Club' offthehookcomedy.com
--     126 | Snappers Fort Myers                  |    159 |    160 | API: 'Snappers Fort Myers' snapperscomedyclub.com
--     128 | Spokane Comedy Club                  |    151 |    152 | API: 'Spokane Comedy Club' spokanecomedyclub.com

UPDATE clubs SET seatengine_id = '158' WHERE id = 64;
UPDATE clubs SET seatengine_id = '245' WHERE id = 65;
UPDATE clubs SET seatengine_id = '218' WHERE id = 66;
UPDATE clubs SET seatengine_id = '163' WHERE id = 74;
UPDATE clubs SET seatengine_id = '125' WHERE id = 81;
UPDATE clubs SET seatengine_id = '297' WHERE id = 87;
UPDATE clubs SET seatengine_id = '290' WHERE id = 102;
UPDATE clubs SET seatengine_id = '285' WHERE id = 107;
UPDATE clubs SET seatengine_id = '204' WHERE id = 122;
UPDATE clubs SET seatengine_id = '160' WHERE id = 126;
UPDATE clubs SET seatengine_id = '152' WHERE id = 128;

-- Nulled out (B) — seatengine_id points to wrong/nonexistent venues;
-- no correct ID found in full enumeration of IDs 1–700.
-- seatengine_classic uses scraping_url at runtime, not seatengine_id.
UPDATE clubs SET seatengine_id = NULL WHERE id IN (
    42,   -- McGuire's Comedy Club
    43,   -- Brokerage Comedy Club
    44,   -- Governors' Comedy Club
    45,   -- Stress Factory
    46,   -- Stress Factory Bridgeport
    47,   -- Comedy In Harlem
    53,   -- Dania Improv
    57,   -- The Comedy Zone Greensboro
    58,   -- The Comedy Zone - Charlotte
    59,   -- Comedy Zone Jacksonville
    60,   -- The Comedy Zone - Cherokee
    67,   -- The Comedy Catch
    69,   -- The Comedy Club of Kansas City
    70,   -- The Comedy Fort
    71,   -- The Comedy Loft of DC
    72,   -- The Comedy Vault
    75,   -- The Dojo of Comedy
    77,   -- The Well Comedy Club
    79,   -- Underground Comedy
    83,   -- Wit's End Comedy Lounge
    88,   -- Barrel Room Portland
    90,   -- Bricktown Comedy Club
    92,   -- Bricky's Comedy Club
    94,   -- Capitol Hill Comedy Bar
    95,   -- Coastal Creative
    97,   -- Comedy Cabin
    104,  -- Desert Ridge Improv
    106,  -- Emerald City Comedy Club
    108,  -- Helium & Elements Restaurant - St. Louis
    114,  -- Laugh Camp Comedy Club
    116,  -- Loonees Comedy Corner
    117,  -- Louisville Comedy Club
    118,  -- Magoobys Joke House
    123,  -- Planet Of The Tapes
    124,  -- Rooster T. Feathers Comedy Club
    127,  -- Snappers Palm Harbor
    129,  -- StandUpLive Phoenix
    130,  -- Stress Factory - Valley Forge
    134   -- Helium Comedy Club - Atlanta
);
