# TASK-1982 - Wiseguys Westgate Disposition

Date: 2026-05-06

## Question

TASK-1954 found that club `586` (`Wiseguys - Westgate`) and its SeatEngine
source were absent from the live database, while the public SeatEngine-hosted
Westgate page rendered. This follow-up determines whether the venue should be
restored as a live club/source, mapped to an existing Wiseguys row, or left
absent with rationale.

## Evidence

- The scraper's own Playwright browser fetched
  `https://westgate.wiseguyscomedy.com` successfully:
  - HTML length: `7595`
  - `<title>`: `Wiseguys - Westgate`
  - links include `/events`, `/calendar`, `/locations`, and the canonical
    Wiseguys site.
- The same Playwright browser fetched the event surfaces:
  - `https://westgate.wiseguyscomedy.com/events`
  - `https://westgate.wiseguyscomedy.com/calendar`
  - both pages identify the venue as `Wiseguys - Westgate` at
    `3000 Paradise Road`, Las Vegas, NV.
  - embedded structured data reports `"Events":[]`; no event/ticket inventory
    is rendered.
- The authenticated SeatEngine client verified the historical venue ID:
  - `GET /api/v1/venues/566` returns venue name `Wiseguys - Westgate`,
    website `https://www.westgate.wiseguyscomedy.com`, timezone
    `America/Los_Angeles`.
  - `GET /api/v1/venues/566/shows` returns `0` shows.
- `https://www.wiseguyscomedy.com/locations` currently lists the six active
  Wiseguys locations already represented in the DB:
  Jordan Landing, The Showroom, Historic Ogden, The Rickles Room, Town Square,
  and The Cabaret. It does not mention Westgate.
- A read-only live DB query found active Wiseguys rows/sources only for those
  six normalized locations. It found no club `586` row and no source for
  SeatEngine venue `566`.
- Migration
  `apps/web/prisma/migrations/20260506101500_normalize_wiseguys_locations/migration.sql`
  intentionally deleted club IDs `448` and `586` as historical/dormant
  SeatEngine stubs when they had no dependent shows or user data.

## Disposition

Do not restore Wiseguys Westgate.

The Westgate SeatEngine page is a live shell, but it has no current shows,
the authenticated SeatEngine API returns zero inventory, and the current
Wiseguys locations page omits Westgate. Restoring the deleted DB row would
reintroduce a dormant venue with no event feed and duplicate the
normalization decision that already limits Wiseguys to the six current
locations.

No DB/source change is needed. Keep club `586` absent unless Westgate appears
again on the canonical Wiseguys locations page or SeatEngine venue `566`
starts returning ticketed shows.
