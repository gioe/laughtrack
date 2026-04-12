-- Batch hide 21 non-comedy SeatEngine bulk-import clubs
-- All have 0 shows, no city/state/address, and are clearly not comedy venues.
-- Identified during backlog grooming 2026-04-12.

-- Club 590: Lowe's Events — retail/event venue, not comedy
-- Club 363: Mario's Neighborhood Bar & Grill — bar/restaurant
-- Club 473: Matt Stanley — individual person, not a venue
-- Club 228: Murder Served Hot — murder mystery dinner theatre
-- Club 356: NW Ghost Tours — ghost tour company
-- Club 368: Nauti Parrot Dock Bar — dock bar
-- Club 235: Nickel City Chef — cooking competition
-- Club 357: Oregon Ghost Conference — ghost conference
-- Club 595: Owens Entertainment and Management — entertainment management company
-- Club 282: Park Avenue Banquet Hall — banquet hall
-- Club 218: Pennsylvania Convention Center — convention center (website is '#')
-- Club 402: Power Watch — non-entertainment SeatEngine account
-- Club 531: R.U.M. Music Group — music group
-- Club 467: Rahmein Presents... — comedy promoter, not a venue
-- Club 500: Reach LA Angels — charity organization
-- Club 353: Sam Tripoli Comedy Show Tickets — individual comedian ticket page
-- Club 624: Tamarac Marina & Restaurant — marina/restaurant
-- Club 322: Mastori's — dead SeatEngine account; Comedy Shoppe (club 327) covers this entity
-- Club 578: Pickwick The Restaurant — restaurant at Pickwick & Frolic; Hilarities (club 113) covers comedy
-- Club 440: Purdue Fort Wayne International BallRoom — dead domain; Fort Wayne Comedy Club (club 107) covers this
-- Club 310: "Please visit our new site..." — stale redirect; Virginia Beach Funny Bone (club 1033) covers this

UPDATE "clubs" SET "visible" = false WHERE "id" IN (
  590, 363, 473, 228, 356, 368, 235, 357, 595, 282,
  218, 402, 531, 467, 500, 353, 624, 322, 578, 440, 310
);
