# TASK-1920 — Eventbrite Empty Organizer Dispositions (2026-05-06)

Follow-up to `task-1916-eventbrite-organizer-urls.md` for the two enabled
Eventbrite organizer feeds that returned zero live events.

## Verification Summary

| club_id | club | organizer_id | scraper API events | disposition | action |
|--------:|------|--------------|-------------------:|-------------|--------|
| 200 | Comedy on Collins | `109625487101` | 0 | dormant Eventbrite feed | leave as-is |
| 510 | Comedy Blvd | `43929578463` | 0 | venue appears inactive/nonexistent | leave as-is |

## Evidence

### club 200 — Comedy on Collins

- Live DB row: `scraping_sources.id=546`, `platform='eventbrite'`,
  `source_url='https://www.eventbrite.com/o/comedy-on-collins-109625487101'`,
  `enabled=TRUE`, `priority=0`; current `shows` count is 0.
- `EventbriteClient.fetch_all_events()` against organizer `109625487101`
  returned 0 live events.
- The organizer is still the same account used by Comedy on Collins' website:
  the current homepage links to Eventbrite event `1599205299099`, and direct
  Eventbrite event lookup reports `organizer_id='109625487101'`.
- That linked event is `status='completed'` with local start
  `2025-08-22T19:30:00`; the other homepage Eventbrite ticket link checked
  (`1528383228379`) is also completed. The configured organizer is therefore
  not stale to a different organizer, but it currently has no live Eventbrite
  inventory.

Disposition note: leave as-is; Comedy on Collins still exists, but the
Eventbrite organizer feed is dormant.

### club 510 — Comedy Blvd

- Live DB rows: enabled Eventbrite source `scraping_sources.id=423`,
  `source_url='https://www.eventbrite.com/o/comedy-blvd-43929578463'`,
  `enabled=TRUE`, `priority=0`; disabled SeatEngine fallback
  `scraping_sources.id=846`; current `shows` count is 0.
- Club row is already hidden (`visible=FALSE`).
- `EventbriteClient.fetch_all_events()` against organizer `43929578463`
  returned 0 live events.
- Eventbrite organizer page still exists and lists no upcoming events; search
  results show only past Comedy Blvd Eventbrite events, with recent examples
  ending in 2024-2025.
- The configured website `https://www.comedyblvdla.com` fails DNS resolution via
  both `curl` and the scraper's Playwright browser. The known Slotted signup
  page `https://slotted.co/comedyblvdsignup/` returns a Slotted 404 page.
- Third-party directory pages still mention the 7924 Beverly Blvd venue, but
  the evidence above does not identify a current replacement ticketing source.

Disposition note: leave as-is; Comedy Blvd appears inactive/nonexistent rather
than migrated to a current replacement URL.
