-- Batch hide 19 non-comedy SeatEngine bulk-import clubs (round 2)
-- All have 0 shows and are clearly not comedy venues.
-- Identified during backlog grooming 2026-04-12.

-- Club 528: Test Site — SeatEngine test data
-- Club 304: Test Venue — SeatEngine test data (website: apple.com)
-- Club 331: The Canby Farmers Market — farmers market
-- Club 625: Tryon Equestrian Center — equestrian center
-- Club 294: Yesha Ministries — religious ministry
-- Club 458: "this site is no longer updated" — dead site notice, website is '#'
-- Club 277: "Portland" — bare city name placeholder, website is '#'
-- Club 276: "Vancouver" — bare city name placeholder, website is '#'
-- Club 312: Summer of Sass Fundraiser — one-time fundraiser event
-- Club 468: The Caravan Fundraisers — fundraiser organization
-- Club 416: The Forum Worlds of Fun — amusement park venue
-- Club 233: Ultimate Males — male entertainment, not comedy
-- Club 358: Walk Oregon City — walking tour company
-- Club 515: Turn 2 Entertainment — entertainment company, no website
-- Club 278: Via Productions — production company
-- Club 366: Newburgh Brewing Company — brewery
-- Club 309: "Syracuse" — duplicate of Syracuse Funny Bone (club 1028); SeatEngine subdomain "funny-bone-syracuse"
-- Club 348: "Seymour Swan" — duplicate of Scotty's Comedy Cove (club 253); same website scottyssteakhouse.com
-- Club 295: "Spring Street Pub" — satellite SeatEngine listing for the Comedy Shoppe (club 327)

UPDATE "clubs" SET "visible" = false WHERE "id" IN (
  528, 304, 331, 625, 294, 458, 277, 276, 312, 468,
  416, 233, 358, 515, 278, 366, 309, 348, 295
);
