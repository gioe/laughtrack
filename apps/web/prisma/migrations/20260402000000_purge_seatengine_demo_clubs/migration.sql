-- Purge 44 SeatEngine demo/test clubs (TASK-881)
-- These are Demo - *, Event #1–8, BBQ & Blues Bash, ILEA Portland,
-- Sam Tripoli: Stand Up Comedian, Ultimate Males, Ultimate Playmates.
-- All have website = '#' or *.seatengine.com test domains and no real shows.
-- Cascades to shows, tickets, and all related records via ON DELETE CASCADE.

DELETE FROM clubs
WHERE id IN (
  231,
  241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252,
  259,
  264, 265,
  280, 281,
  286,
  337,
  347,
  401,
  403,
  418, 419, 420, 421, 422,
  425, 426,
  428,
  430, 431,
  436, 437,
  439,
  443,
  445,
  466,
  471,
  560
);
