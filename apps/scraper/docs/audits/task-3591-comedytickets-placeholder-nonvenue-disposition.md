# TASK-3591 ComedyTickets Placeholder And Non-Venue Disposition

ComedyTickets remains a discovery signal only. This task resolves the 15
placeholder, room-split, festival, class, cruise, and city-only rows routed from
TASK-3587, plus one existing enabled source URL that contained a ComedyTickets
branded SeatEngine host.

## Migration

`apps/web/prisma/migrations/20260706160000_resolve_comedytickets_placeholder_nonvenue_candidates/migration.sql`

The migration:

- Inserts hidden non-routeable clubs for event-specific, festival, class/open-mic,
  room-without-parent, and city-only placeholder rows.
- Adds disabled `custom` / `none` scraping sources with `source_url = NULL`; the
  ComedyTickets URL is retained only as disabled audit metadata.
- Adds canonical aliases for known room/time-slot variants:
  - `Comedy Store - Los Angeles (Belly Room)` -> club `158` (`The Comedy Store`)
  - `Neon Room at Helium Comedy Club` -> club `133` (`Helium Comedy Club - Portland`)
  - `Skyline Comedy Club - 7PM` -> club `1057` (`Skyline Comedy Club`)
- Leaves `Lexington, KY` as a physical-address merge to club `100`
  (`Comedy Off Broadway`) and intentionally avoids a broad city-name alias.
- Replaces the enabled `Let''s Comedy` source URL
  `http://letscomedytickets.seatengine.com` with the first-party events URL
  `https://www.letscomedyftw.com/events`, preserving the SeatEngine venue id.

## Duplicate Protection

The hidden club inserts are exact-name guarded. Known room/time-slot variants are
guarded through `club_aliases` using the normalized alias/city/state unique key.
The Lexington row is protected by the existing physical address on Comedy Off
Broadway instead of a broad city alias.

## Output

The row-level disposition table is:

`apps/scraper/docs/audits/task-3591-comedytickets-placeholder-nonvenue-disposition.csv`
