# TASK-2469: World Stage Ticket Target Audit

Date: 2026-05-26
Club: The Lounge at World Stage, club 1353
Source: `scraping_sources` platform `custom`, scraper_key `world_stage`
(Ciright calendar API at `https://www.myciright.com/Ciright/api/worldcafelive/m3203760`)

## Persisted ticket URLs

Current rows for club 1353 use two distinct `purchase_url` shapes:

| Shape | Rows | Show date range | Origin |
| --- | --- | --- | --- |
| `https://worldstage.live/shows` (generic shows page) | 38 | 2026-05-08 → 2026-09-19 | current `world_stage` Ciright scraper |
| `https://www.etix.com/ticket/p/<id>/<slug>?gclid=` (per-event) | 14 | 2026-04-17 → 2026-06-20 | legacy Etix scraper, pre-Ciright migration |

The 38 generic-page rows are produced by the live `world_stage` scraper: each
`WorldStageEvent.to_show` builds a single fallback ticket via
`ShowFactoryUtils.create_fallback_ticket(source_url)`, and `source_url` is the
configured `worldstage.live/shows` page. The 14 per-event Etix rows are historical
— they were scraped directly from Etix detail pages before the venue rebranded
(worldcafelive.org → worldstage.live) and the scraper was migrated to the Ciright
API (the Etix path now returns a DataDome iframe; see `metadata.task_2009_audit`).

## Does the Ciright source carry per-event purchase URLs?

No. A live POST to the Ciright endpoint returned 70 rows (30 in The Lounge,
roomId 3131060). Every row exposes only internal calendar fields:

```
buildingColorCode, childEvent, childEventId, childEventList, colorCode,
createdBy, createdById, createdDate, decription, endDate, eventId, eventName,
room, roomId, startDate, status, statusId, subStatus, subStatusId, textColor,
time, updatedBy, updatedById, updatedDate
```

There is **no** purchase/ticket/link field. A regex sweep of the entire JSON
response found zero `http(s)://` URLs of any kind. The only `eventId` /
`childEventId` values are Ciright's internal booking IDs, not Etix product IDs,
so they cannot be turned into a per-event Etix link either. The Ciright source
genuinely lacks per-event purchase targets.

## Live ticket flow verification

Drove `https://worldstage.live/shows` (the venue's own published calendar, fed by
the same Ciright API). For all 10 events on page 1 — and inside the per-event
detail modal (verified on "Ladies First: R&B Dinner Party 1") — the **"Get Tickets"**
button resolves to a single, identical, venue-level Etix URL:

```
https://www.etix.com/ticket/v/1599/music-hall-at-world-cafe-live
```

This is the generic Etix venue landing page (`/ticket/v/1599/`, still carrying the
stale "world-cafe-live" branding), not a per-event product page (`/ticket/p/<id>/`).
The venue itself publishes no per-event purchase link anywhere — list view or modal.

## Conclusion

The generic `worldstage.live/shows` target is **correct** and needs no event-specific
remediation. There is no per-event purchase target to map to:

- The Ciright API exposes no purchase URLs at all.
- The venue's own site routes every show to one generic Etix venue page.

The current target is also the **preferred** choice over the generic Etix venue link:
it keeps users on the venue's own site (project convention: drive traffic to the
venue), whereas the Etix link is equally generic and still mis-branded "world-cafe-live".

Recovering per-event Etix product URLs (the `/ticket/p/<id>/` shape the 14 legacy rows
use) would require scraping the DataDome-protected Etix path that the Ciright migration
was specifically built to avoid — not worth re-introducing for a non-event-specific gain.

No code change recommended. The legacy per-event Etix rows can be left to age out
naturally as the Ciright scraper supersedes them.
