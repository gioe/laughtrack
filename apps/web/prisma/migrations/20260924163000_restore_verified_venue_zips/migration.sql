-- TASK-4044: Source-verified missing US venue ZIPs, audited 2026-09-24.
-- Evidence: apps/scraper/docs/audits/2026-09-24-venue-zips/sources.json.
-- Identity/address/country guards prevent applying stale evidence after a move.
-- Fill-only and idempotent: never replace existing postal data.
WITH verified(id, name, address, country, zip_code) AS (
  VALUES
    (61, 'Goodnights Comedy Club', '401 Woodburn Rd., Raleigh, NC 27605', NULL, '27605'),
    (80, 'Uptown Theater', '270 Broadway Providence, RI 02903', 'US', '02903'),
    (96, 'Comedy Cabana', '9588 N Kings Hwy, Myrtle Beach, SC 29572', NULL, '29572'),
    (99, 'Comedy Magic Cabaret', '843 William Hilton Pkwy, Hilton Head Island, SC 29928', NULL, '29928'),
    (102, 'DC Improv', '1140 Connecticut Ave NW, Washington, DC 20036', NULL, '20036'),
    (139, 'Helium Comedy Club - Indianapolis', '10 W Georgia St, Indianapolis, IN 46225, USA', 'US', '46225'),
    (142, 'Goofs Comedy Club', '432 McGrath Highway, Somerville, MA 02143', 'US', '02143'),
    (217, 'Comedy Connection', '39 Warren Ave, East Providence, RI 02914, USA', 'US', '02914'),
    (288, 'Dead Crow Comedy', '511 N 3rd St, Wilmington, NC 28401, USA', 'US', '28401'),
    (409, 'Hotbed - DC Comedy Club', '2477 18th St NW, Washington, DC 20009, USA', 'US', '20009'),
    (412, 'AC Jokes', '1133 Boardwalk, Atlantic City, NJ 08401, USA', 'US', '08401'),
    (475, 'Harvelle''s Santa Monica', '1432 4th St, Santa Monica, CA 90401, USA', 'US', '90401'),
    (476, 'Harvelle''s Long Beach', '201 E Broadway, Long Beach, CA 90802, USA', 'US', '90802'),
    (479, 'Riddles Comedy Club', '5055 W 111th St, Alsip, IL 60803, USA', 'US', '60803'),
    (480, 'Governor''s Levittown', '90 Division Ave, Levittown, NY 11756, USA', 'US', '11756'),
    (481, 'The Brokerage in Bellmore', '2797 Merrick Rd, Bellmore, NY 11710, USA', 'US', '11710'),
    (482, 'McGuires in Bohemia', '1627 Smithtown Ave, Bohemia, NY 11716, USA', 'US', '11716'),
    (486, 'Mic Drop Comedy', '8878 Clairemont Mesa Blvd', NULL, '92123'),
    (519, 'Juke Box Comedy Club', '3527 W Farmington Rd, Peoria, IL 61604, USA', 'US', '61604'),
    (524, 'Give a Hoot Comedy Club', '16143 Shady Grove Rd, Gaithersburg, MD 20877, USA', 'US', '20877'),
    (542, 'The Alley Stage', '11 Anderson St SE, Marietta, GA 30064, USA', 'US', '30064'),
    (548, 'Krackpots Comedy Club', '14 Lincoln Way W, Massillon, OH 44647, USA', 'US', '44647'),
    (562, 'The Hickory Premier', '109 11th St NW, Hickory, NC 28601, USA', 'US', '28601'),
    (565, 'Poe''s Magic Theatre', 'Lord Baltimore Hotel, 20 W Baltimore St The, Baltimore, MD 21201, USA', 'US', '21201'),
    (572, 'View Street Tavern', '92 View St, Chicopee, MA 01020, USA', 'US', '01020'),
    (579, 'The Function Comedy Club and Cocktail Lounge', '1414 Market St, San Francisco, CA 94102, USA', 'US', '94102'),
    (592, 'BABS Comedy Club', '7316 Madison St, Forest Park, IL 60130, USA', 'US', '60130'),
    (611, 'New Orleans Comedy Room', '8700 Lake Forest Blvd, New Orleans, LA 70127, USA', 'US', '70127'),
    (622, 'Dunlap''s Corner Bar', '3258 W 32nd St, Cleveland, OH 44109, USA', 'US', '44109'),
    (628, 'Dharma Bums', '4935 River Rd, New Hope, PA 18938, USA', 'US', '18938'),
    (629, 'The Comedy Club of Lawrence', '811 New Hampshire St, Lawrence, KS 66044, USA', 'US', '66044'),
    (632, 'Springfield Comedy Club', '420 W College St, Springfield, MO 65806, USA', 'US', '65806'),
    (633, 'Stardome Comedy Club', '1818 Data Dr, Hoover, AL 35244, USA', 'US', '35244'),
    (634, 'Mic Drop Comedy Detroit', '2301 Woodward Ave, Detroit, MI 48201, USA', 'US', '48201'),
    (636, 'Wicked Funny Comedy Club Danvers', '126 Newbury St, Danvers, MA 01923, USA', NULL, '01923'),
    (637, 'Wicked Funny Comedy Club Salisbury', '98 Beach Rd, Salisbury, MA 01952, USA', NULL, '01952'),
    (638, 'Harrisburg Comedy Zone', '110 Limekiln Rd, New Cumberland, PA 17070, USA', 'US', '17070'),
    (1035, 'American Comedy Company', '818 Sixth Ave, San Diego, CA 92101, USA', 'US', '92101'),
    (1036, 'Comedy Works Downtown', '1226 15th St, Denver, CO 80202, USA', 'US', '80202'),
    (1348, 'The KillBox Comedy Club', '1305 E Tallmadge Ave, Akron, OH 44310, USA', 'US', '44310'),
    (2368, 'Reilly Arts Center', '500 NE 9th St, Ocala, FL 34470, USA', 'US', '34470'),
    (2571, 'James K. Polk Theater', '505 Deaderick St, Nashville, TN 37243, USA', 'US', '37243'),
    (2577, 'Patchogue Theatre for the Performing Arts', '71 E Main St, Patchogue, NY 11772, USA', 'US', '11772'),
    (3001, 'Fox Theatre', 'Fox Theatre, 2211 Woodward Ave, Detroit, MI 48201, USA', 'US', '48201'),
    (8699, 'Atomic Comedy Co.', '133 W Pike St, Canonsburg, PA 15317, USA', 'US', '15317'),
    (8703, 'The Brothers Lounge', '11609 Detroit Ave, Cleveland, OH 44102, USA', 'US', '44102'),
    (8714, 'The Auricle - Venue & Bar', '201 Cleveland Ave NW, Canton, OH 44702, USA', 'US', '44702'),
    (8901, 'KeyBank State Theatre', '1519 Euclid Ave, Cleveland, OH 44115', 'US', '44115')
)
UPDATE clubs AS c SET zip_code = v.zip_code
FROM verified AS v
WHERE c.id = v.id AND c.name = v.name
  AND c.address IS NOT DISTINCT FROM v.address
  AND c.country IS NOT DISTINCT FROM v.country
  AND c.visible = TRUE
  AND NULLIF(BTRIM(c.zip_code), '') IS NULL;
