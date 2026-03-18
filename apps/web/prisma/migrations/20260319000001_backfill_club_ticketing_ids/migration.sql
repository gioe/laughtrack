-- Backfill seatengine_id for all 80 clubs with scraper='seatengine'.
-- IDs were extracted from each venue's SeatEngine CDN asset URLs.

-- ── Pre-existing NYC/NJ area clubs ─────────────────────────────────────────
UPDATE clubs SET seatengine_id = '443' WHERE id = 42;  -- McGuire's Comedy Club
UPDATE clubs SET seatengine_id = '442' WHERE id = 43;  -- Brokerage Comedy Club
UPDATE clubs SET seatengine_id = '441' WHERE id = 44;  -- Governors' Comedy Club
UPDATE clubs SET seatengine_id = '310' WHERE id = 45;  -- Stress Factory (New Brunswick)
UPDATE clubs SET seatengine_id = '311' WHERE id = 46;  -- Stress Factory Bridgeport
UPDATE clubs SET seatengine_id = '466' WHERE id = 47;  -- Comedy In Harlem
UPDATE clubs SET seatengine_id = '420' WHERE id = 53;  -- Dania Improv

-- ── Comedy Zone group ──────────────────────────────────────────────────────
UPDATE clubs SET seatengine_id = '448' WHERE id = 57;  -- The Comedy Zone Greensboro
UPDATE clubs SET seatengine_id = '402' WHERE id = 58;  -- The Comedy Zone - Charlotte
UPDATE clubs SET seatengine_id = '453' WHERE id = 59;  -- Comedy Zone Jacksonville
UPDATE clubs SET seatengine_id = '504' WHERE id = 60;  -- The Comedy Zone - Cherokee
UPDATE clubs SET seatengine_id = '449' WHERE id = 73;  -- The Comedy Zone Greenville

-- ── North Carolina ────────────────────────────────────────────────────────
UPDATE clubs SET seatengine_id = '53'  WHERE id = 61;  -- Goodnights Comedy Club

-- ── Pacific Northwest ──────────────────────────────────────────────────────
UPDATE clubs SET seatengine_id = '508' WHERE id = 62;  -- Sunken Bus Studios
UPDATE clubs SET seatengine_id = '157' WHERE id = 64;  -- Tacoma Comedy Club

-- ── Various ───────────────────────────────────────────────────────────────
UPDATE clubs SET seatengine_id = '230' WHERE id = 65;  -- The Caravan
UPDATE clubs SET seatengine_id = '206' WHERE id = 66;  -- The Comedy Attic
UPDATE clubs SET seatengine_id = '425' WHERE id = 67;  -- The Comedy Catch
UPDATE clubs SET seatengine_id = '417' WHERE id = 68;  -- The Comedy Chateau
UPDATE clubs SET seatengine_id = '338' WHERE id = 69;  -- The Comedy Club of Kansas City
UPDATE clubs SET seatengine_id = '401' WHERE id = 70;  -- The Comedy Fort
UPDATE clubs SET seatengine_id = '298' WHERE id = 71;  -- The Comedy Loft of DC
UPDATE clubs SET seatengine_id = '389' WHERE id = 72;  -- The Comedy Vault
UPDATE clubs SET seatengine_id = '162' WHERE id = 74;  -- The Comic Strip (El Paso)
UPDATE clubs SET seatengine_id = '392' WHERE id = 75;  -- The Dojo of Comedy
UPDATE clubs SET seatengine_id = '99'  WHERE id = 76;  -- The Velveeta Room
UPDATE clubs SET seatengine_id = '487' WHERE id = 77;  -- The Well Comedy Club
UPDATE clubs SET seatengine_id = '227' WHERE id = 78;  -- Tommy T's Pleasanton
UPDATE clubs SET seatengine_id = '368' WHERE id = 79;  -- Underground Comedy
UPDATE clubs SET seatengine_id = '472' WHERE id = 82;  -- Wicked Funny Comedy Club North Andover
UPDATE clubs SET seatengine_id = '519' WHERE id = 83;  -- Wit's End Comedy Lounge

-- ── National chains / multisite ────────────────────────────────────────────
UPDATE clubs SET seatengine_id = '2'   WHERE id = 84;  -- Acme Comedy Company
UPDATE clubs SET seatengine_id = '422' WHERE id = 85;  -- Arlington Drafthouse
UPDATE clubs SET seatengine_id = '11'  WHERE id = 86;  -- Baltimore Comedy Factory
UPDATE clubs SET seatengine_id = '282' WHERE id = 87;  -- Bananas Comedy Club Renaissance Hotel
UPDATE clubs SET seatengine_id = '324' WHERE id = 88;  -- Barrel Room Portland
UPDATE clubs SET seatengine_id = '524' WHERE id = 89;  -- Beaches Comedy Club
UPDATE clubs SET seatengine_id = '359' WHERE id = 90;  -- Bricktown Comedy Club (OKC)
UPDATE clubs SET seatengine_id = '452' WHERE id = 91;  -- Bricktown Comedy Club Tulsa
UPDATE clubs SET seatengine_id = '561' WHERE id = 92;  -- Bricky's Comedy Club
UPDATE clubs SET seatengine_id = '3'   WHERE id = 93;  -- Cap City Comedy Club
UPDATE clubs SET seatengine_id = '64'  WHERE id = 99;  -- Comedy Magic Cabaret
UPDATE clubs SET seatengine_id = '434' WHERE id = 100; -- Comedy Off Broadway
UPDATE clubs SET seatengine_id = '475' WHERE id = 101; -- Cozzys Comedy Club
UPDATE clubs SET seatengine_id = '275' WHERE id = 102; -- DC Improv
UPDATE clubs SET seatengine_id = '444' WHERE id = 103; -- Denver Comedy Underground
UPDATE clubs SET seatengine_id = '328' WHERE id = 104; -- Desert Ridge Improv
UPDATE clubs SET seatengine_id = '432' WHERE id = 105; -- Elmwood Commons Theater
UPDATE clubs SET seatengine_id = '588' WHERE id = 106; -- Emerald City Comedy Club
UPDATE clubs SET seatengine_id = '270' WHERE id = 107; -- Fort Wayne Comedy Club @ 469
UPDATE clubs SET seatengine_id = '132' WHERE id = 108; -- Helium & Elements Restaurant - St. Louis
UPDATE clubs SET seatengine_id = '1'   WHERE id = 110; -- Helium Comedy Club (Philadelphia)
UPDATE clubs SET seatengine_id = '538' WHERE id = 113; -- Hilarities 4th Street Theatre
UPDATE clubs SET seatengine_id = '537' WHERE id = 114; -- Laugh Camp Comedy Club
UPDATE clubs SET seatengine_id = '457' WHERE id = 115; -- Laughs Unlimited
UPDATE clubs SET seatengine_id = '460' WHERE id = 116; -- Loonees Comedy Corner
UPDATE clubs SET seatengine_id = '414' WHERE id = 117; -- Louisville Comedy Club
UPDATE clubs SET seatengine_id = '301' WHERE id = 118; -- Magoobys Joke House
UPDATE clubs SET seatengine_id = '552' WHERE id = 119; -- Mic Drop Comedy Plano
UPDATE clubs SET seatengine_id = '478' WHERE id = 120; -- Mic Drop Mania
UPDATE clubs SET seatengine_id = '463' WHERE id = 121; -- Nate Jackson's Super Funny Comedy Club
UPDATE clubs SET seatengine_id = '192' WHERE id = 122; -- Off The Hook Comedy Club
UPDATE clubs SET seatengine_id = '419' WHERE id = 123; -- Planet Of The Tapes
UPDATE clubs SET seatengine_id = '483' WHERE id = 124; -- Rooster T. Feathers Comedy Club
UPDATE clubs SET seatengine_id = '493' WHERE id = 125; -- Sticks and Stones Comedy Club
UPDATE clubs SET seatengine_id = '159' WHERE id = 126; -- Snappers Fort Myers
UPDATE clubs SET seatengine_id = '587' WHERE id = 127; -- Snappers Palm Harbor
UPDATE clubs SET seatengine_id = '151' WHERE id = 128; -- Spokane Comedy Club
UPDATE clubs SET seatengine_id = '336' WHERE id = 129; -- StandUpLive Phoenix
UPDATE clubs SET seatengine_id = '601' WHERE id = 130; -- Stress Factory - Valley Forge
UPDATE clubs SET seatengine_id = '424' WHERE id = 131; -- Summit City Comedy Club
UPDATE clubs SET seatengine_id = '21'  WHERE id = 132; -- Helium & Elements Restaurant - Buffalo
UPDATE clubs SET seatengine_id = '5'   WHERE id = 133; -- Helium Comedy Club - Portland
UPDATE clubs SET seatengine_id = '530' WHERE id = 134; -- Helium Comedy Club - Atlanta
UPDATE clubs SET seatengine_id = '499' WHERE id = 63;  -- TK's Comedy
UPDATE clubs SET seatengine_id = '124' WHERE id = 81;  -- Vermont Comedy Club

-- ── Fix clubs mis-assigned to seatengine (they use other platforms) ─────────
-- Comedy Key West uses Tixologi ticketing; no seatengine presence.
UPDATE clubs SET scraper = 'json_ld', scraping_url = 'www.comedykeywest.com/shows', seatengine_id = NULL WHERE id = 98;

-- Uptown Theater (Providence) is a custom Next.js site, not SeatEngine.
UPDATE clubs SET scraper = 'json_ld', scraping_url = 'www.uptownpvd.com/events', seatengine_id = NULL WHERE id = 80;

-- Capitol Hill Comedy Bar (id=94) is a redirect to Emerald City Comedy Club (id=106,
-- seatengine_id=588). Deactivate to prevent duplicate show ingestion.
UPDATE clubs SET visible = false WHERE id = 94;

-- ── Fix Eventbrite clubs ────────────────────────────────────────────────────
-- Bushwick Comedy Club has a dedicated 'bushwick' scraper; not eventbrite.
UPDATE clubs SET scraper = 'bushwick' WHERE id = 19;

-- Caveat NYC: Eventbrite venue ID 253402413 (venue name "2277 3rd Ave").
UPDATE clubs SET eventbrite_id = '253402413', scraping_url = 'www.eventbrite.com' WHERE id = 15;

-- Comic Strip Live: Eventbrite venue ID 296430132 (venue name "The Comic Strip").
UPDATE clubs SET eventbrite_id = '296430132', scraping_url = 'www.eventbrite.com' WHERE id = 21;

-- Union Hall: Eventbrite venue ID 35619335.
UPDATE clubs SET eventbrite_id = '35619335', scraping_url = 'www.eventbrite.com' WHERE id = 9;
