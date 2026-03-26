-- TASK-710: Fix 20 SeatEngine v1 seatengine_id mismatches
-- Each club's seatengine_id was pointing to the wrong SeatEngine venue.
-- Correct IDs were verified by:
--   (a) cross-referencing the names returned by GET /api/v1/venues/{id}
--   (b) enumerating the full ID space (1-649) and matching by API venue name + website URL
--
-- club_id | DB name                              | old_id | new_id | evidence
--      62 | Sunken Bus Studios                   |    508 |    523 | website sunkenbus.com, API name match
--      63 | TK's                                 |    499 |    514 | website tkscomedy.com, API name match
--      68 | The Comedy Chateau                   |    417 |    432 | API name 'The Comedy Chateau', website comedychateau.seatengine.com
--      73 | The Comedy Zone Greenville           |    449 |    464 | website greenvillecomedyzone.com, API name match
--      78 | Tommy T's Pleasanton                 |    227 |    242 | website tommyts.com, API name match
--      82 | Wicked Funny Comedy Club N. Andover  |    472 |    487 | website wickedfunnynorthandover.com, API name match
--      85 | Arlington Drafthouse                 |    422 |    437 | website arlingtondrafthouse.seatengine.com, API name match
--      89 | Beaches Comedy Club                  |    524 |    543 | website beachescomedyclub.com, API name match
--      91 | Bricktown Comedy Club Tulsa          |    452 |    467 | website bricktowntulsa.com, API name match
--     100 | Comedy Off Broadway                  |    434 |    449 | website comedyoffbroadway.com, API name match
--     101 | Cozzys Comedy Club                   |    475 |    490 | website cozzys.com, API name match
--     103 | Denver Comedy Underground            |    444 |    459 | website denvercomedyunderground.seatengine.com, name match
--     105 | Elmwood Commons Theater              |    432 |    447 | website robsplayhousetheater.com, API name match
--     113 | Hilarities 4th Street Theatre        |    538 |    557 | website hilarities.com, API name match
--     115 | Laughs Unlimited                     |    457 |    472 | website laughsunlimited.com, API name match
--     119 | Mic Drop Comedy Plano                |    552 |    571 | website micdropcomedyplano.com, API name match
--     120 | Mic Drop Mania                       |    478 |    493 | website micdropcomedychandler.com, API name match
--     121 | Nate Jackson's Super Funny Comedy    |    463 |    478 | website superfunnycomedyclub.com, API name match
--     125 | Sticks and Stones Comedy Club        |    493 |    508 | website sticksandstonescomedyclub.com, API name match
--     131 | Summit City Comedy Club              |    424 |    439 | website summitcity.seatengine.com, API name match

UPDATE clubs SET seatengine_id = '523' WHERE id = 62;
UPDATE clubs SET seatengine_id = '514' WHERE id = 63;
UPDATE clubs SET seatengine_id = '432' WHERE id = 68;
UPDATE clubs SET seatengine_id = '464' WHERE id = 73;
UPDATE clubs SET seatengine_id = '242' WHERE id = 78;
UPDATE clubs SET seatengine_id = '487' WHERE id = 82;
UPDATE clubs SET seatengine_id = '437' WHERE id = 85;
UPDATE clubs SET seatengine_id = '543' WHERE id = 89;
UPDATE clubs SET seatengine_id = '467' WHERE id = 91;
UPDATE clubs SET seatengine_id = '449' WHERE id = 100;
UPDATE clubs SET seatengine_id = '490' WHERE id = 101;
UPDATE clubs SET seatengine_id = '459' WHERE id = 103;
UPDATE clubs SET seatengine_id = '447' WHERE id = 105;
UPDATE clubs SET seatengine_id = '557' WHERE id = 113;
UPDATE clubs SET seatengine_id = '472' WHERE id = 115;
UPDATE clubs SET seatengine_id = '571' WHERE id = 119;
UPDATE clubs SET seatengine_id = '493' WHERE id = 120;
UPDATE clubs SET seatengine_id = '478' WHERE id = 121;
UPDATE clubs SET seatengine_id = '508' WHERE id = 125;
UPDATE clubs SET seatengine_id = '439' WHERE id = 131;
