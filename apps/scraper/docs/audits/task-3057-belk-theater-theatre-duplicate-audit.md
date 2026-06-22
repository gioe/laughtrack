# TASK-3057: Belk Theater/Theatre Duplicate Audit

## Decision

Club 5337 (`Belk Theatre`) is a true duplicate of club 5037 (`Belk Theater`).
Keep club 5037 as canonical and fold club 5337 into it.

## Evidence

Blumenthal Arts' official venue page uses `Belk Theater` and lists the venue at
130 North Tryon Street in Charlotte, North Carolina:
https://www.blumenthalarts.org/venues/detail/belk-theater

Both club rows describe the same physical venue:

| Field | Canonical 5037 | Duplicate 5337 |
| --- | --- | --- |
| Name | Belk Theater | Belk Theatre |
| City/state | Charlotte, NC | Charlotte, NC |
| Address | 130 N. Tyron St., Charlotte, NC | 130 North Tryon street, Charlotte, NC |
| Google place ID | ChIJMU44uCSgVogRxzbX_XDOEpI | ChIJMU44uCSgVogRxzbX_XDOEpI |
| Coordinates | 35.2273169, -80.8415419 | 35.2273169, -80.8415419 |
| Timezone | America/New_York | America/New_York |
| Status | active, visible | active, visible |

Source routing should stay on club 5037 as canonical. Club 5037 has enabled
`scraping_sources.id=4127`, platform `ticketmaster`, scraper key
`ticketmaster_comedy`, and Ticketmaster venue ID `KovZpZAEknIA`. Club 5337 has
enabled `scraping_sources.id=4427`, platform `ticketmaster`, scraper key
`ticketmaster_comedy`, and Ticketmaster venue ID `ZFr9jZdFvF`.

There are currently no Belk Theater/Theatre aliases. Future duplicate prevention
needs a verified `Belk Theatre` alias on club 5037, and the alternate
Ticketmaster source row from club 5337 should be moved to club 5037 disabled so
ID-first Ticketmaster upserts resolve to the canonical row.

## Show Overlap

Club 5337 has 2 shows. Both collide exactly with club 5037 by `(date, room)` and
have the same show URL.

| Duplicate show | Canonical show | Date | Name |
| --- | --- | --- | --- |
| 2876816 | 2841036 | 2026-08-22T23:00:00+00:00 | HASAN HATES RONNY \| RONNY HATES HASAN |
| 2841660 | 2876210 | 2026-10-24T23:00:00+00:00 | Anthony Jeselnik: Wrath Of The Man |

The duplicate Hasan Hates Ronny row was last scraped by `ticketmaster_comedy`;
the canonical row was last scraped by `ticketmaster_national`. For Anthony
Jeselnik, the duplicate row was last scraped by `ticketmaster_national`; the
canonical row was last scraped by `ticketmaster_comedy`.

## Dependent Rows

Direct references on club 5337:

| Table | Count |
| --- | ---: |
| shows | 2 |
| ticket_purchase_click_events | 8 |
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
| tickets | 2 |
| lineup_items | 3 |
| tagged_shows | 4 |
| sent_notifications | 0 |
| ticket_purchase_click_events by show | 8 |

Each canonical show already has corresponding lineup, tagged show, and ticket
rows. The fold should still use conflict-safe copy/insert steps before deleting
the duplicate shows, following the existing duplicate-club fold scripts, so any
non-identical child data is preserved.

## Safe Fold Plan

1. Add a verified `Belk Theatre` alias to club 5037 with city `Charlotte`, state
   `NC`, and source `TASK-3057`.
2. Move club 5337's Ticketmaster source row to club 5037 disabled with a new
   non-conflicting priority and metadata noting the TASK-3057 fold.
3. Build a temporary show map from club 5337 to club 5037 by exact `(date, room)`.
   Assert the map contains exactly 2 rows and no unmapped duplicate shows.
4. Repoint `ticket_purchase_click_events.show_id` from duplicate shows to the
   mapped canonical shows, and set `club_id=5037` for any click events that still
   point at club 5337.
5. Conflict-safely copy child rows from duplicate shows to canonical shows where
   needed:
   - `lineup_items`
   - `tagged_shows`
   - `tickets`
   - `sent_notifications` if rows ever appear before execution
6. Delete the 2 duplicate shows from club 5337 after click events and child rows
   have been preserved.
7. Move `scraper_run_clubs` rows from club 5337 to club 5037.
8. Close club 5337:
   - Set `visible=false`.
   - Set `status='closed'`.
   - Set `closed_at=NOW()`.
   - Set `total_shows=0`.
   - Rename to `Belk Theatre (duplicate of club 5037; folded from club 5337)`.
   - Append a description note that TASK-3057 identified it as a duplicate of
     club 5037.
9. Recompute `total_shows` for club 5037.
10. Add postconditions:
   - Club 5337 has zero direct references in the dependent tables listed above.
   - Club 5337 has zero shows.
   - Club 5037 remains active and visible.

## Non-Duplicate Alternative

This is not a separate room and not merely source metadata. The two rows share
the same Google place ID, coordinates, address, city/state, and exact show keys.
There is no reason to preserve club 5337 as a distinct venue row.
