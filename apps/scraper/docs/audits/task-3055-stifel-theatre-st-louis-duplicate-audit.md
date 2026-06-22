# TASK-3055: Stifel Theatre St. Louis Duplicate Audit

## Decision

Club 7557 (`Stifel Theatre`) is a true duplicate of club 2509 (`Stifel Theatre - St. Louis`).
Keep club 2509 as canonical and fold club 7557 into it.

## Evidence

Both club rows describe the same physical venue:

| Field | Canonical 2509 | Duplicate 7557 |
| --- | --- | --- |
| Name | Stifel Theatre - St. Louis | Stifel Theatre |
| City/state | St. Louis, MO | Saint Louis, MO |
| Address | 1400 Market Street | 1400 Market Street, Saint Louis, MO |
| Google place ID | ChIJuVL1IBSz2IcRaPfuSyqnmH8 | ChIJuVL1IBSz2IcRaPfuSyqnmH8 |
| Coordinates | 38.6280216, -90.2018122 | 38.6280216, -90.2018122 |
| Timezone | America/Chicago | America/Chicago |
| Website | https://www.stifeltheatre.com | empty |
| Status | active, visible | active, visible |

Source routing also points at club 2509 as canonical. Club 2509 has enabled
`scraping_sources.id=2348`, platform `ticketmaster`, scraper key `live_nation`,
Ticketmaster venue ID `KovZpa3die`, and source URL
`https://www.ticketmaster.com/stifel-theatre-tickets-saint-louis/venue/50474`.
Club 7557 has no `scraping_sources` rows.

The current alias coverage is incomplete for the duplicate-producing payload.
There is one alias on club 2509:

| Alias | City/state | Source |
| --- | --- | --- |
| Stifel Theatre - St. Louis | St. Louis, MO | 20260515170000_onboard_stifel_theatre_ticketmaster |

The duplicate row likely survived the national Ticketmaster upsert because
Ticketmaster emitted `name='Stifel Theatre'` and `city='Saint Louis'`; the
alias matcher queries aliases inside an exact `(city, state)` lookup, so the
existing `St. Louis` alias was not visible for `Saint Louis`.

## Show Overlap

Club 7557 has 3 shows. All 3 collide exactly with club 2509 by `(date, room)`
and have the same Ticketmaster event URL.

| Duplicate show | Canonical show | Date | Name |
| --- | --- | --- | --- |
| 2894106 | 1794125 | 2026-10-17T00:30:00+00:00 | Nurse John: Against Medical Advice Tour |
| 2894107 | 1794126 | 2026-10-19T00:00:00+00:00 | Leanne Morgan: THE TIME OF OUR LIVES TOUR |
| 2894108 | 2094847 | 2026-11-23T00:30:00+00:00 | Je'Caryous Johnson Presents "Set It Off" |

The duplicate shows were last scraped by `ticketmaster_national`; the canonical
shows were last scraped by `live_nation`.

## Dependent Rows

Direct references on club 7557:

| Table | Count |
| --- | ---: |
| shows | 3 |
| ticket_purchase_click_events | 8 |
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
| tagged_shows | 7 |
| sent_notifications | 0 |
| ticket_purchase_click_events by show | 8 |

Each canonical show already has corresponding lineup, tagged show, and ticket
rows. The fold should still use conflict-safe copy/insert steps before deleting
the duplicate shows, following the existing duplicate-club fold scripts, so any
non-identical child data is preserved.

## Safe Fold Plan

1. Add verified aliases to club 2509:
   - `Stifel Theatre`, city `Saint Louis`, state `MO`, source `TASK-3055`.
   - Optional: keep or upsert `Stifel Theatre - St. Louis`, city `St. Louis`,
     state `MO`, source `TASK-3055` if the existing migration source should be
     annotated with this audit.
2. Build a temporary show map from club 7557 to club 2509 by exact `(date, room)`.
   Assert the map contains exactly 3 rows and no unmapped duplicate shows.
3. Repoint `ticket_purchase_click_events.show_id` from duplicate shows to the
   mapped canonical shows, and set `club_id=2509` for any click events that
   still point at club 7557.
4. Conflict-safely copy child rows from duplicate shows to canonical shows where
   needed:
   - `lineup_items`
   - `tagged_shows`
   - `tickets`
   - `sent_notifications` if rows ever appear before execution
5. Delete the 3 duplicate shows from club 7557 after click events and child rows
   have been preserved.
6. Leave source routing on club 2509. There are no source rows to move from club
   7557. Do not disable source 2348; it is the canonical enabled source.
7. Close club 7557:
   - Set `visible=false`.
   - Set `status='closed'`.
   - Set `closed_at=NOW()`.
   - Set `total_shows=0`.
   - Rename to `Stifel Theatre (duplicate of club 2509; folded from club 7557)`.
   - Append a description note that TASK-3055 identified it as a duplicate of
     club 2509.
8. Recompute `total_shows` for club 2509.
9. Add postconditions:
   - Club 7557 has zero direct references in the dependent tables listed above.
   - Club 7557 has zero shows.
   - Club 2509 remains active and visible.
   - No active visible duplicate group remains for normalized Stifel Theatre in
     Missouri.

## Non-Duplicate Alternative

This is not a separate room and not just display-name metadata. The two rows
share the same Google place ID, coordinates, address, Ticketmaster event URLs,
and exact show keys. There is no reason to preserve club 7557 as a distinct
venue row.
