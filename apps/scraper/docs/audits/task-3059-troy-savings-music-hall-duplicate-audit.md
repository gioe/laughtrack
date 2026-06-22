# TASK-3059: Troy Savings Music Hall Duplicate Audit

## Decision

Club 5038 (`Troy Savings Music Hall`) is a true duplicate of club 2579
(`Troy Savings Bank Music Hall`). Keep club 2579 as canonical and fold club 5038
into it.

## Evidence

The official venue site uses `Troy Savings Bank Music Hall` and lists the venue
at `30 Second Street, Troy, NY 12180`:
https://www.troymusichall.org/

Both club rows describe the same physical venue:

| Field | Canonical 2579 | Duplicate 5038 |
| --- | --- | --- |
| Name | Troy Savings Bank Music Hall | Troy Savings Music Hall |
| City/state | Troy, NY | Troy, NY |
| Address | 30 Second Street | 30 2nd St, Troy, NY |
| Website | https://www.troymusichall.org/ | |
| Google place ID | ChIJ4akrgwcP3okROKDH6fEfhGk | ChIJ4akrgwcP3okROKDH6fEfhGk |
| Coordinates | 42.7304978, -73.6912905 | 42.7304978, -73.6912905 |
| Timezone | America/New_York | America/New_York |
| Status | active, visible | active, visible |

Source routing should stay on club 2579. Club 2579 has enabled
`scraping_sources.id=2375`, platform `custom`, scraper key
`troy_savings_bank_music_hall`, and official source URL
`https://www.troymusichall.org/events/?searchType=7`. It also has disabled
`scraping_sources.id=1587`, the original `tour_dates` source. Club 5038 has
enabled `scraping_sources.id=4128`, platform `ticketmaster`, scraper key
`ticketmaster_comedy`, and Ticketmaster venue ID `ZFr9jZeFA7`.

There are currently no Troy Savings Music Hall aliases. Future duplicate
prevention needs a verified `Troy Savings Music Hall` alias on club 2579, and
the alternate Ticketmaster source row from club 5038 should be moved to club
2579 disabled so ID-first Ticketmaster upserts resolve to the canonical row.

## Show Overlap

Club 5038 has 1 show. It collides with club 2579 by exact `(date, room)`.

| Duplicate show | Canonical show | Date | Duplicate name | Canonical name |
| --- | --- | --- | --- | --- |
| 2841037 | 1874853 | 2026-08-22T23:00:00+00:00 | Please Don't Destroy | Please Don’t Destroy: LIVE |

The URLs differ because the duplicate row came from Ticketmaster while the
canonical row came from the venue-owned scraper:

| Row | URL |
| --- | --- |
| Duplicate | https://www.ticketmaster.com/event/Z7r9jZ1A70AoK |
| Canonical | https://www.troymusichall.org/events/3017/please-don-t-destroy-live/? |

The official event page confirms the same event at Troy Savings Bank Music Hall
on August 22, 2026 at 7:00 PM:
https://www.troymusichall.org/events/3017/please-don-t-destroy-live/

## Dependent Rows

Direct references on club 5038:

| Table | Count |
| --- | ---: |
| shows | 1 |
| ticket_purchase_click_events | 5 |
| scraping_sources enabled | 1 |
| scraper_run_clubs | 4 |
| favorite_clubs | 0 |
| tagged_clubs | 0 |
| club_image_assets | 0 |
| processed_emails | 0 |
| production_company_venues | 0 |
| eventbrite_organizer_venues | 0 |
| email_subscriptions | 0 |

Child rows below the duplicate show:

| Table | Count |
| --- | ---: |
| tickets | 1 |
| lineup_items | 1 |
| tagged_shows | 2 |
| sent_notifications | 0 |
| ticket_purchase_click_events by show | 5 |

The canonical show already has a ticket and tags, but no lineup rows. The fold
should use conflict-safe copy/insert steps before deleting the duplicate show so
the duplicate lineup is preserved.

## Safe Fold Plan

1. Add a verified `Troy Savings Music Hall` alias to club 2579 with city `Troy`,
   state `NY`, and source `TASK-3059`.
2. Move club 5038's Ticketmaster source row to club 2579 disabled with a new
   non-conflicting priority and metadata noting the TASK-3059 fold.
3. Build a temporary show map from club 5038 to club 2579 by exact `(date, room)`.
   Assert there are no unmapped duplicate shows.
4. Repoint `ticket_purchase_click_events.show_id` from the duplicate show to the
   mapped canonical show, and set `club_id=2579` for any click events that still
   point at club 5038.
5. Conflict-safely copy child rows from the duplicate show to the canonical show
   where needed:
   - `lineup_items`
   - `tagged_shows`
   - `tickets`
   - `sent_notifications` if rows ever appear before execution
6. Delete the duplicate show from club 5038 after click events and child rows
   have been preserved.
7. Move `scraper_run_clubs` rows from club 5038 to club 2579.
8. Close club 5038:
   - Set `visible=false`.
   - Set `status='closed'`.
   - Set `closed_at=NOW()`.
   - Set `total_shows=0`.
   - Rename to `Troy Savings Music Hall (duplicate of club 2579; folded from club 5038)`.
   - Append a description note that TASK-3059 identified it as a duplicate of
     club 2579.
9. Recompute `total_shows` for club 2579.
10. Add postconditions:
   - Club 5038 has zero direct references in the dependent tables listed above.
   - Club 5038 has zero shows.
   - Club 2579 remains active and visible.

## Non-Duplicate Alternative

This is not a separate room and not merely source metadata. The two rows share
the same Google place ID, coordinates, address, city/state, and event key. There
is no reason to preserve club 5038 as a distinct venue row.
