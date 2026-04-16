-- Close J Spot Comedy Club NC (club 822)
-- Phantom venue: NC-specific domain (jspotcomedyclubnc.com) does not resolve
-- SeatEngine API 404 for venue 256 and all plausible slugs (subdomain shows generic SeatEngine landing page, not provisioned)
-- Listed address (7361 Six Forks Rd, Raleigh) is Six Forks Cinemas, not a standalone comedy club
-- Listed phone is an LA area code (818) — appears to be stale spin-off of the now-closed LA J Spot
-- No NC-tied social media activity; no operating venue exists
UPDATE clubs SET visible = false, status = 'closed', closed_at = NOW() WHERE id = 822;
