# The Setup Chicago

## DB Snapshot

| Field | Value |
|---|---|
| Club ID | 660 |
| Name | The Setup Chicago |
| Website | https://setupcomedy.com |
| Location | Chicago, IL, US |
| Status | active |
| Visible | true |
| DB show rows | 0 |
| Upcoming shows | 0 |
| Last show | never |

## Scraping Sources

| Source ID | Platform | Scraper key | Source URL | Enabled | Priority |
|---:|---|---|---|---|---:|
| 138 | stagetime | setup | Google Sheets CSV, gid 0 | true | 0 |

## Current Assessment

The Setup Chicago appears to be winding down or no longer publicly listed as an active Setup city. The configured Stagetime CSV source is fetchable but contains only the header row. The club has never produced show rows in the database.

Official-site checks on 2026-05-06 support disabling the row instead of treating this as a scraper failure:

- `https://setupcomedy.com/chicago` returns HTTP 404.
- The scraper's Playwright browser fetched the 404 page successfully; it contained no Chicago page content.
- `https://setupcomedy.com/vancouver` returns HTTP 200 and renders as `Vancouver - The Setup`, so the parent site and the shared Stagetime pattern are still live for other cities.
- The homepage title is `The Setup Comedy: Underground Stand Up Shows in SF, LA, and NYC`, which omits Chicago.
- The homepage still contains stale links to `/chicago`, but those links resolve to the missing Chicago page.

Implemented recommendation: hide club 660 and disable scraping source 138 with a metadata stamp. Keep `status='active'` because there is no explicit closure or hiatus announcement; this is a reversible visibility/source disable pending any future restored Chicago page or feed rows.

## Investigation Checklist

- [x] Verify the configured source is fetchable.
- [x] Verify whether the source has upcoming rows.
- [x] Verify the official Chicago page.
- [x] Compare against the sibling Vancouver page/source pattern.
- [x] Record the final action and evidence in this note.

## Notes

- Initial reason for audit: active, visible club with zero upcoming shows as of 2026-05-01.
- Investigation timestamp: 2026-05-06 14:40 EDT.
- Configured source 138 CSV result: `date,day,time,title,venue,city,ticket_url,urgency_tag,sold_out`.
- DB show query for club 660 returned `0` total rows and `0` future rows.
- Migration: `apps/web/prisma/migrations/20260506184500_hide_setup_chicago/migration.sql`.
