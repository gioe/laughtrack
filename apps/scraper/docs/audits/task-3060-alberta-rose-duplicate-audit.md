# TASK-3060: Alberta Rose Duplicate Audit

## Decision

Club 5359 (`ALBERTA ROSE`) is a true duplicate of club 5358
(`Alberta Rose Theatre`). Keep club 5358 as canonical and fold club 5359 into
it.

## Evidence

The official venue site uses `Alberta Rose Theatre` and lists the venue at
`3000 NE Alberta Street, Portland, OR 97211`:
https://albertarosetheatre.com/

Both club rows describe the same physical venue:

| Field | Canonical 5358 | Duplicate 5359 |
| --- | --- | --- |
| Name | Alberta Rose Theatre | ALBERTA ROSE |
| City/state | Portland, OR | Portland, OR |
| Address | 3000 NE Alberta St, Portland, OR | 3000 NE ALBERTA, Portland, OR |
| Website | | |
| Google place ID | ChIJbXuuhN6mlVQRRB0icjpP16g | ChIJbXuuhN6mlVQRRB0icjpP16g |
| Coordinates | 45.5589574, -122.6347217 | 45.5589574, -122.6347217 |
| Timezone | America/Los_Angeles | America/Los_Angeles |
| Status | active, visible | active, visible |

Source routing should stay on club 5358. Club 5358 has enabled
`scraping_sources.id=4448`, platform `ticketmaster`, scraper key
`ticketmaster_comedy`, and Ticketmaster venue ID `ZFr9jZ1617`. Club 5359 has
disabled `scraping_sources.id=4449`, platform `ticketmaster`, scraper key
`ticketmaster_comedy`, and alternate Ticketmaster venue ID `KovZpa4spe`.

There are currently no Alberta Rose aliases. Future duplicate prevention needs
a verified `ALBERTA ROSE` alias on club 5358, and the disabled alternate
Ticketmaster source row from club 5359 should be moved to club 5358 disabled so
ID-first Ticketmaster upserts resolve to the canonical row.

## Show Overlap

Club 5359 has 1 show. It collides with club 5358 by exact `(date, room)`, and
the names and Ticketmaster URLs are identical.

| Duplicate show | Canonical show | Date | Duplicate name | Canonical name |
| --- | --- | --- | --- | --- |
| 2841687 | 2841686 | 2026-11-05T03:30:00+00:00 | Davide De Pierro | Davide De Pierro |

| Row | URL |
| --- | --- |
| Duplicate | https://www.ticketmaster.com/event/Z7r9jZ1A7-Ir3 |
| Canonical | https://www.ticketmaster.com/event/Z7r9jZ1A7-Ir3 |

## Dependent Rows

Direct references on club 5359:

| Table | Count |
| --- | ---: |
| shows | 1 |
| ticket_purchase_click_events | 2 |
| scraping_sources enabled | 0 |
| scraping_sources all | 1 |
| scraper_run_clubs | 3 |
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
| ticket_purchase_click_events by show | 2 |

The canonical show already has a ticket, lineup row, and tags. The fold should
still use conflict-safe copy/insert steps before deleting the duplicate show so
the script remains safe if rows change between audit and execution.

## Safe Fold Plan

1. Add a verified `ALBERTA ROSE` alias to club 5358 with city `Portland`,
   state `OR`, and source `TASK-3060`.
2. Move club 5359's disabled Ticketmaster source row to club 5358 disabled with
   a new non-conflicting priority and metadata noting the TASK-3060 fold.
3. Build a temporary show map from club 5359 to club 5358 by exact `(date, room)`.
   Assert there are no unmapped duplicate shows.
4. Repoint `ticket_purchase_click_events.show_id` from the duplicate show to the
   mapped canonical show, and set `club_id=5358` for any click events that still
   point at club 5359.
5. Conflict-safely copy child rows from the duplicate show to the canonical show
   where needed:
   - `lineup_items`
   - `tagged_shows`
   - `tickets`
   - `sent_notifications` if rows ever appear before execution
6. Delete the duplicate show from club 5359 after click events and child rows
   have been preserved.
7. Move `scraper_run_clubs` rows from club 5359 to club 5358.
8. Close club 5359:
   - Set `visible=false`.
   - Set `status='closed'`.
   - Set `closed_at=NOW()`.
   - Set `total_shows=0`.
   - Rename to `ALBERTA ROSE (duplicate of club 5358; folded from club 5359)`.
   - Append a description note that TASK-3060 identified it as a duplicate of
     club 5358.
9. Recompute `total_shows` for club 5358.
10. Add postconditions:
   - Club 5359 has zero direct references in the dependent tables listed above.
   - Club 5359 has zero shows.
   - Club 5358 remains active and visible.

## Non-Duplicate Alternative

This is not a separate room and not merely source metadata. The two rows share
the same Google place ID, coordinates, address, city/state, and event key. There
is no reason to preserve club 5359 as a distinct venue row.
