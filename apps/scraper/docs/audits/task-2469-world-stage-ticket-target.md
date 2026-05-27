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

Follow-up TASK-2486 found that this venue page can render per-event Etix product
links and price ranges when Etix allows the request through. That means the
TASK-2469 conclusion was too strong: the venue-owned World Stage calendar still
does not expose per-event purchase links, but Etix venue `1599` is a potential
secondary source for ticket enrichment.

The legacy Etix venue id `26727` is not Lounge-specific enough to switch back to
blindly, and venue `1599` is the broader Music Hall at World Stage / World Cafe
Live Etix venue. Its listing may include Main Hall shows as well as Lounge shows.
Because club 1353 is specifically The Lounge, Ciright `roomId=3131060` remains
the authoritative event backbone.

Local scraper-stack verification on 2026-05-27:

```
EtixScraper venue_id=1599 -> HTTP 403
Playwright fallback -> DataDome challenge HTML
parsed Etix events -> 0
```

GitHub Actions runner verification on 2026-05-27 used
`Scraper Verify (Single Club)` run `26511493243` against club 1353 on branch
`feature/TASK-2486-etix-world-stage-enrichment`. The job completed
successfully because Ciright still produced 30 Lounge events, but Etix
enrichment did not clear DataDome on the runner:

```
HTTP 403 when fetching ...upcomingEvents/venue?venue_id=1599...
[HttpClient] Triggering Playwright fallback ... (reason: 'HTTP 403')
[PlaywrightBrowser] DataDome interactive CAPTCHA detected but CAPSOLVER_API_KEY is unset
[HttpClient] Playwright fallback ... also returned a bot-block page (signature: 'datadome')
Etix enrichment found no usable events for https://www.etix.com/ticket/v/1599/music-hall-at-world-stage
WorldStageScraper ... 30 confirmed event(s) from Ciright (room_ids=[3131060])
```

This confirms local curl_cffi/Playwright is still blocked. The scraper now treats
Etix as best-effort enrichment only: it fetches venue `1599`, matches Etix rows
back to already room-filtered Ciright rows by title and date, and upgrades only
matched ticket URLs/prices. If Etix is blocked, the scraper keeps the existing
Ciright rows and generic `worldstage.live/shows` ticket target rather than
dropping the venue's reliable calendar.

## Updated conclusion

The generic `worldstage.live/shows` target is still the correct reliable fallback
and room-filtered source. It should not be replaced wholesale by Etix because:

- The Ciright API exposes no purchase URLs at all.
- The venue's own World Stage site routes every show to one generic Etix venue page.
- Etix venue `1599` is not proven Lounge-only and may include Main Hall inventory.
- Etix is still DataDome-blocked from local scraper-stack verification.

The remediation is enrichment, not replacement: keep Ciright for event identity
and room filtering, then use Etix venue `1599` opportunistically to upgrade
matched rows to per-event `/ticket/p/<id>/...` purchase URLs and real prices when
the scraper environment can reach Etix.
