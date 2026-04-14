-- Hide non-comedy SeatEngine clubs with active shows
-- Each venue was individually verified via its website on 2026-04-14

-- Chris' Jazz Cafe (id 213) — jazz club, no comedy programming
UPDATE clubs SET visible = false WHERE id = 213;

-- Rosa's Lounge (id 477) — blues venue, no comedy
UPDATE clubs SET visible = false WHERE id = 477;

-- BoatYard Lake Norman (id 446) — restaurant/live music tribute bands, no comedy
UPDATE clubs SET visible = false WHERE id = 446;

-- All American Magic Theater (id 340) — magic theater, no comedy
UPDATE clubs SET visible = false WHERE id = 340;

-- Magique In Paradise (id 603) — magic/mentalism theater, no comedy
UPDATE clubs SET visible = false WHERE id = 603;

-- Lotus Education & Arts Foundation (id 570) — world music & arts festival, no comedy
UPDATE clubs SET visible = false WHERE id = 570;

-- NOTE: Poe's Magic Theatre (id 565) was investigated but KEPT visible —
-- it hosts stand-up comedy & improv alongside magic shows
