# TASK-3056: Tampa Theatre Spelling Duplicate Audit

## Decision

Club 5356 (`Tampa Theater`) is a true duplicate of club 2584 (`Tampa Theatre`).
Keep club 2584 as canonical and fold club 5356 into it.

## Evidence

Both club rows describe the same physical venue:

| Field | Canonical 2584 | Duplicate 5356 |
| --- | --- | --- |
| Name | Tampa Theatre | Tampa Theater |
| City/state | Tampa, FL | Tampa, FL |
| Address | 711 N Franklin St, Tampa, FL 33602, USA | 711 N Franklin St, Tampa, FL |
| Google place ID | ChIJ98cKiInEwogRfyDonUPi2bc | ChIJ98cKiInEwogRfyDonUPi2bc |
| Coordinates | 27.9503523, -82.4589293 | 27.9503523, -82.4589293 |
| Timezone | America/New_York | America/New_York |
| Status | active, visible | active, visible |

Source routing should stay on club 2584 as canonical. Club 2584 has enabled
`scraping_sources.id=4313`, platform `ticketmaster`, scraper key `live_nation`,
and Ticketmaster venue ID `KovZpZAFAnEA`. Club 5356 has enabled
`scraping_sources.id=4446`, platform `ticketmaster`, scraper key
`ticketmaster_comedy`, and Ticketmaster venue ID `ZFr9jZdFaa`.

There are currently no Tampa Theatre aliases. Future duplicate prevention needs
a verified `Tampa Theater` alias on club 2584, and the alternate Ticketmaster
source row from club 5356 should be moved to club 2584 disabled so ID-first
Ticketmaster upserts resolve to the canonical row.

## Show Overlap

Club 5356 has 3 shows. All 3 collide exactly with club 2584 by `(date, room)`
and have the same show URL.

| Duplicate show | Canonical show | Date | Name |
| --- | --- | --- | --- |
| 2876845 | 2841460 | 2026-10-03T00:00:00+00:00 | Atsuko Okatsuka: The Big Bowl Tour |
| 2876846 | 2841461 | 2026-10-16T23:30:00+00:00 | Bassem Youssef: The Belly of the Beast Tour |
| 2841684 | 2841462 | 2026-11-02T00:00:00+00:00 | Daniel Sloss |

The duplicate Atsuko Okatsuka and Bassem Youssef rows were last scraped by
`ticketmaster_comedy`; the duplicate Daniel Sloss row was last scraped by
`ticketmaster_national`. The canonical rows were last scraped by `live_nation`.

## Dependent Rows

Direct references on club 5356:

| Table | Count |
| --- | ---: |
| shows | 3 |
| ticket_purchase_click_events | 2 |
| scraping_sources enabled | 1 |
| scraper_run_clubs | 4 |
| favorite_clubs | 0 |
| tagged_clubs | 0 |
| club_image_assets | 0 |
| processed_emails | 0 |
| production_company_venues | 0 |
| eventbrite_organizer_venues | 0 |
| email_subscriptions | 0 |

Child rows below the duplicate shows:

| Table | Count |
| --- | ---: |
| tickets | 3 |
| lineup_items | 3 |
| tagged_shows | 6 |
| sent_notifications | 0 |
| ticket_purchase_click_events by show | 2 |

Each canonical show already has corresponding lineup, tagged show, and ticket
rows. The fold should still use conflict-safe copy/insert steps before deleting
the duplicate shows, following the existing duplicate-club fold scripts, so any
non-identical child data is preserved.

## Safe Fold Plan

1. Add a verified `Tampa Theater` alias to club 2584 with city `Tampa`, state
   `FL`, and source `TASK-3056`.
2. Move club 5356's Ticketmaster source row to club 2584 disabled with a new
   non-conflicting priority and metadata noting the TASK-3056 fold.
3. Build a temporary show map from club 5356 to club 2584 by exact `(date, room)`.
   Assert the map contains exactly 3 rows and no unmapped duplicate shows.
4. Repoint `ticket_purchase_click_events.show_id` from duplicate shows to the
   mapped canonical shows, and set `club_id=2584` for any click events that
   still point at club 5356.
5. Conflict-safely copy child rows from duplicate shows to canonical shows where
   needed:
   - `lineup_items`
   - `tagged_shows`
   - `tickets`
   - `sent_notifications` if rows ever appear before execution
6. Delete the 3 duplicate shows from club 5356 after click events and child rows
   have been preserved.
7. Move `scraper_run_clubs` rows from club 5356 to club 2584.
8. Close club 5356:
   - Set `visible=false`.
   - Set `status='closed'`.
   - Set `closed_at=NOW()`.
   - Set `total_shows=0`.
   - Rename to `Tampa Theater (duplicate of club 2584; folded from club 5356)`.
   - Append a description note that TASK-3056 identified it as a duplicate of
     club 2584.
9. Recompute `total_shows` for club 2584.
10. Add postconditions:
   - Club 5356 has zero direct references in the dependent tables listed above.
   - Club 5356 has zero shows.
   - Club 2584 remains active and visible.

## Non-Duplicate Alternative

This is not a separate room and not merely source metadata. The two rows share
the same Google place ID, coordinates, address, city/state, and exact show keys.
There is no reason to preserve club 5356 as a distinct venue row.
