# TASK-3061: Uptown Theatre Providence Duplicate Audit

## Decision

Club 4509 (`Uptown Theatre Providence`) is a true duplicate of club 80
(`Uptown Theater`). Keep club 80 as canonical and fold club 4509 into it.

## Evidence

The official venue site uses `Uptown Theater` and lists the venue at
`270 Broadway, Providence, RI 02903`:
https://www.uptownpvd.com/

Both club rows describe the same physical venue:

| Field | Canonical 80 | Duplicate 4509 |
| --- | --- | --- |
| Name | Uptown Theater | Uptown Theatre Providence |
| City/state | Providence, RI | Providence, RI |
| Address | 270 Broadway Providence, RI 02903 | 270 Broadway, Providence, RI |
| Website | https://www.uptownpvd.com | |
| Google place ID | ChIJV1yw5XRF5IkRnd48L1zOJIE | ChIJV1yw5XRF5IkRnd48L1zOJIE |
| Coordinates | 41.820136, -71.4262485 | 41.820136, -71.4262485 |
| Timezone | America/New_York | America/New_York |
| Status | active, visible | active, visible |

Source routing should stay on club 80. Club 80 has enabled
`scraping_sources.id=101`, platform `custom`, scraper key `json_ld`, and source
URL `www.uptownpvd.com/events`. Club 4509 has enabled
`scraping_sources.id=3599`, platform `ticketmaster`, scraper key
`ticketmaster_comedy`, and Ticketmaster venue ID `Z7r9jZak1X`.

Club 80 also has disabled `scraping_sources.id=1904`, platform `tour_dates`.
Its metadata points at an Akaash Singh Minneapolis ticket URL from
`https://concerts50.com/buy/akaash-singh-in-minneapolis-tickets-apr-25-2026`
and sample URL `https://akaashsinghtour.com/`. That metadata is unrelated
historical tour-date noise, not evidence for a separate Providence venue row.

There are currently no Uptown aliases. Future duplicate prevention needs a
verified `Uptown Theatre Providence` alias on club 80, and the duplicate
Ticketmaster source row from club 4509 should be moved to club 80 disabled so
Ticketmaster ID-first upserts resolve to the canonical row without re-enabling
the duplicate source.

## Show Overlap

Club 4509 has 1 show. It collides with club 80 by exact `(date, room)`.

| Duplicate show | Canonical show | Date | Duplicate name | Canonical name |
| --- | --- | --- | --- | --- |
| 2828048 | 1364924 | 2026-06-13T23:00:00+00:00 | Please Don't Destroy | Please Don’t Destroy: LIVE |

The URLs differ because the duplicate row came from Ticketmaster while the
canonical row came from the venue-owned JSON-LD scraper:

| Row | URL |
| --- | --- |
| Duplicate | https://www.ticketmaster.com/event/Z7r9jZ1A70kAF |
| Canonical | https://www.uptownpvd.com/events/please-dont-destroy-live |

The official event page confirms the same event at Uptown Theater on
June 13, 2026 at 7:00 PM:
https://www.uptownpvd.com/events/please-dont-destroy-live

## Dependent Rows

Direct references on club 4509:

| Table | Count |
| --- | ---: |
| shows | 1 |
| ticket_purchase_click_events | 3 |
| scraping_sources enabled | 1 |
| scraping_sources all | 1 |
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
| ticket_purchase_click_events by show | 3 |

The canonical show already has a ticket and tags, but no lineup row. The fold
should use conflict-safe copy/insert steps before deleting the duplicate show so
the duplicate lineup is preserved.

## Safe Fold Plan

1. Add a verified `Uptown Theatre Providence` alias to club 80 with city
   `Providence`, state `RI`, and source `TASK-3061`.
2. Move club 4509's Ticketmaster source row to club 80 disabled with a new
   non-conflicting priority and metadata noting the TASK-3061 fold.
3. Leave club 80's disabled tour_dates source row disabled; it is unrelated
   historical metadata and should not affect the fold decision.
4. Build a temporary show map from club 4509 to club 80 by exact `(date, room)`.
   Assert there are no unmapped duplicate shows.
5. Repoint `ticket_purchase_click_events.show_id` from the duplicate show to the
   mapped canonical show, and set `club_id=80` for any click events that still
   point at club 4509.
6. Conflict-safely copy child rows from the duplicate show to the canonical show
   where needed:
   - `lineup_items`
   - `tagged_shows`
   - `tickets`
   - `sent_notifications` if rows ever appear before execution
7. Delete the duplicate show from club 4509 after click events and child rows
   have been preserved.
8. Move `scraper_run_clubs` rows from club 4509 to club 80.
9. Close club 4509:
   - Set `visible=false`.
   - Set `status='closed'`.
   - Set `closed_at=NOW()`.
   - Set `total_shows=0`.
   - Rename to `Uptown Theatre Providence (duplicate of club 80; folded from club 4509)`.
   - Append a description note that TASK-3061 identified it as a duplicate of
     club 80.
10. Recompute `total_shows` for club 80.
11. Add postconditions:
   - Club 4509 has zero direct references in the dependent tables listed above.
   - Club 4509 has zero shows.
   - Club 80 remains active and visible.

## Non-Duplicate Alternative

This is not a separate room and not merely source metadata. The two rows share
the same Google place ID, coordinates, address, city/state, and event key. The
tour-date metadata on club 80 points to an unrelated Minneapolis event and does
not justify preserving club 4509 as a distinct venue row.
