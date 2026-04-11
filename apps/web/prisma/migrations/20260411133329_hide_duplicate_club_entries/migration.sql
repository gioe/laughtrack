-- Hide duplicate club entries identified by TASK-1422 audit.
-- Each duplicate shares the same venue as the canonical entry but has
-- fewer (or zero) shows and/or a less complete profile.
--
-- Canonical → Duplicate (reason)
-- 47  Comedy In Harlem           → 505  Comedy in Harlem                        (fewer shows: 65 vs 395)
-- 125 Sticks and Stones          → 532  STICKS AND STONES COMEDY CLUB           (fewer shows: 11 vs 272, same website)
-- 175 Sunset Strip Comedy Club   → 571  Sunset Strip                            (0 shows, same website)
-- 122 Off The Hook Comedy Club   → 582  Off The Hook Comedy Club Tax Exempt     (0 shows, tax-exempt SeatEngine variant)
-- 606 One Mike Detroit           → 607  One Mike Detroit Events                 (0 shows, no website)
-- 529 The Dope Show              → 535  The Dope Show CA                        (0 shows, no website)
-- 485 LAUGH IT UP COMEDY CLUB    → 631  Laugh It Up Comedy                     (0 shows, no website)
-- 367 Laff House                 → 283  Laff House Old                         (0 shows, name says "Old")
-- 105 Elmwood Commons Theater    → 525  Elmwood Commons Playhouse Theater      (0 shows, seatengine.cloud URL)
-- 469 Let's Comedy               → 410  Let's Comedy Venues                    (0 shows)
-- 855 Laugh Tonight Comedy       → 449  Laugh Tonight Comedy @ Laugh Factory   (same website, same single show)
-- 850 Bananas Comedy Club        → 87   Bananas Comedy Club Renaissance Hotel  (fewer shows: 33 vs 50, no location data)

UPDATE clubs SET visible = false WHERE id IN (
  505,  -- Comedy in Harlem (dup of 47)
  532,  -- STICKS AND STONES COMEDY CLUB (dup of 125)
  571,  -- Sunset Strip (dup of 175)
  582,  -- Off The Hook Comedy Club Tax Exempt (dup of 122)
  607,  -- One Mike Detroit Events (dup of 606)
  535,  -- The Dope Show CA (dup of 529)
  631,  -- Laugh It Up Comedy (dup of 485)
  283,  -- Laff House Old (dup of 367)
  525,  -- Elmwood Commons Playhouse Theater (dup of 105)
  410,  -- Let's Comedy Venues (dup of 469)
  449,  -- Laugh Tonight Comedy @ Laugh Factory (dup of 855)
  87    -- Bananas Comedy Club Renaissance Hotel (dup of 850)
);
