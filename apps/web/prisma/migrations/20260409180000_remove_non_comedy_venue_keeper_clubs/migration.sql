-- Remove 6 non-comedy "venue keeper" clubs from SeatEngine bulk-import
-- None have shows, tags, or subscriptions — safe to delete directly.
--
-- ID=824  Grand Lodge of Texas        — Masonic fraternal lodge, no events
-- ID=790  The Hotel Somerset-Bridgewater — Hotel, website returns 503
-- ID=789  MJ's Buttonwood (Buttonwood Manor) — Wedding/catering venue
-- ID=785  Don the Beachcomber          — Tiki bar/restaurant, 0 SeatEngine events
-- ID=842  Tavola Ristorante           — Italian restaurant in Rome, Italy
-- ID=838  Food Precinct               — Restaurant in Kokomo, IN, site down (502)

DELETE FROM clubs WHERE id IN (785, 789, 790, 824, 838, 842);
