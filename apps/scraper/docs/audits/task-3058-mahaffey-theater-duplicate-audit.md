# TASK-3058: Mahaffey Theater Duplicate Audit

## Decision

Club 7516 (`Duke Energy Center for the Arts - Mahaffey Theater`) is a true
duplicate of club 2507 (`Mahaffey Theater - Duke Energy Center for the Arts FL`).
Keep club 2507 as canonical because it owns the enabled Ticketmaster source and
existing history, but rename it to the official venue name:
`Duke Energy Center for the Arts - Mahaffey Theater`.

## Evidence

The official site identifies itself as the official website and ticketing source
for `The Duke Energy Center for the Arts - Mahaffey Theater`, and lists the venue
at `400 First Street South, St. Petersburg, FL 33701`:
https://themahaffey.com/

Both club rows describe the same physical venue:

| Field | Canonical 2507 | Duplicate 7516 |
| --- | --- | --- |
| Name | Mahaffey Theater - Duke Energy Center for the Arts FL | Duke Energy Center for the Arts - Mahaffey Theater |
| City/state | Saint Petersburg, FL | St Petersburg, FL |
| Address | 400 First Street South | 400 1st Street S, St Petersburg, FL |
| Website | https://themahaffey.com/ | |
| Google place ID | ChIJSWCg1pvhwogR-rDr1SAB-vY | ChIJSWCg1pvhwogR-rDr1SAB-vY |
| Coordinates | 27.767067, -82.6321408 | 27.767067, -82.6321408 |
| Timezone | America/New_York | America/New_York |
| Status | active, visible | active, visible |

Source routing should stay on club 2507. Club 2507 has enabled
`scraping_sources.id=2343`, platform `ticketmaster`, scraper key `live_nation`,
and Ticketmaster venue ID `KovZpZAdE1eA`. It also has disabled
`scraping_sources.id=1515`, the original `tour_dates` source that was replaced by
the verified Ticketmaster onboarding. Club 7516 has no `scraping_sources` rows.

Club 2507 already has verified aliases for:

- `Duke Energy Center for the Arts - Mahaffey Theater`
- `Mahaffey Theater`
- `Mahaffey Theater at the Duke Energy Center for the Arts`

Those aliases use city `Saint Petersburg`. Future duplicate prevention should
also preserve the legacy canonical string and the duplicate row's `St Petersburg`
city spelling as verified aliases on club 2507.

## Show Overlap

Club 7516 has 2 shows. Both collide exactly with club 2507 by `(date, room)` and
have the same show URL.

| Duplicate show | Canonical show | Date | Name |
| --- | --- | --- | --- |
| 2894023 | 1794117 | 2026-10-09T23:30:00+00:00 | Nurse John: Against Medical Advice Tour |
| 3145588 | 3024659 | 2026-12-18T00:00:00+00:00 | JOSH JOHNSON'S COMEDY BAND CAMP |

The duplicate rows were last scraped by `ticketmaster_national`; the canonical
rows were last scraped by `live_nation`.

## Dependent Rows

Direct references on club 7516:

| Table | Count |
| --- | ---: |
| shows | 2 |
| ticket_purchase_click_events | 0 |
| scraping_sources | 0 |
| scraper_run_clubs | 0 |
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
| lineup_items | 2 |
| tagged_shows | 6 |
| sent_notifications | 0 |
| ticket_purchase_click_events by show | 0 |

Each canonical show already has corresponding lineup, tagged show, and ticket
rows. The fold should still use conflict-safe copy/insert steps before deleting
the duplicate shows, following the existing duplicate-club fold scripts, so any
non-identical child data is preserved.

## Safe Fold Plan

1. Rename club 2507 to the official name
   `Duke Energy Center for the Arts - Mahaffey Theater`.
2. Add or refresh verified aliases on club 2507 with source `TASK-3058`:
   - `Duke Energy Center for the Arts - Mahaffey Theater`, city `Saint Petersburg`
   - `Duke Energy Center for the Arts - Mahaffey Theater`, city `St Petersburg`
   - `Mahaffey Theater - Duke Energy Center for the Arts FL`, city `Saint Petersburg`
   - `Mahaffey Theater`, city `St Petersburg`
3. Keep club 2507's enabled `live_nation` Ticketmaster source as canonical.
   There are no source rows on club 7516 to move or disable.
4. Build a temporary show map from club 7516 to club 2507 by exact `(date, room)`.
   Assert the map contains exactly 2 rows and no unmapped duplicate shows.
5. Conflict-safely copy child rows from duplicate shows to canonical shows where
   needed:
   - `lineup_items`
   - `tagged_shows`
   - `tickets`
   - `sent_notifications` if rows ever appear before execution
6. Delete the 2 duplicate shows from club 7516 after child rows have been
   preserved.
7. Close club 7516:
   - Set `visible=false`.
   - Set `status='closed'`.
   - Set `closed_at=NOW()`.
   - Set `total_shows=0`.
   - Rename to
     `Duke Energy Center for the Arts - Mahaffey Theater (duplicate of club 2507; folded from club 7516)`.
   - Append a description note that TASK-3058 identified it as a duplicate of
     club 2507.
8. Recompute `total_shows` for club 2507.
9. Add postconditions:
   - Club 7516 has zero direct references in the dependent tables listed above.
   - Club 7516 has zero shows.
   - Club 2507 remains active and visible.

## Non-Duplicate Alternative

This is not a separate room and not merely source metadata. The two rows share
the same Google place ID, coordinates, address, state, and exact show keys. There
is no reason to preserve club 7516 as a distinct venue row.
