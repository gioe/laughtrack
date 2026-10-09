# Hartford Funny Bone direct coverage

Verified 2026-10-09 for TASK-4145.

## Identity and gap

- Canonical club **4904**, Hartford Funny Bone, 194 Buckland Hills Drive,
  Manchester, CT 06042. Existing verified alias: Funny Bone Comedy Club - Hartford.
  Prior duplicate 9432 was folded under TASK-3321 and is no longer present.
- Only one future show was stored: Jeff Allen, October 29. Its Ticketmaster
  national feed refreshed it October 9. No active direct source existed.
- Source 3994 (`ticketmaster_comedy`, venue Z7r9jZa7ef) is intentionally disabled
  by the national-feed cutover. Keep its identifier and disabled state.
- Club timezone was incorrectly `Etc/GMT`. Ticketmaster's importer localizes its
  localDate/localTime using the club timezone. The official calendar confirms
  Jeff Allen at 7pm Eastern; existing show 4942927 was stored at 19:00 UTC.
  Correct that exact row to 23:00 UTC in place, preserving references, and set
  the club timezone to `America/New_York` before direct ingestion.

## Native source and chosen configuration

The scraper's native HTTP stack retrieved the complete
<https://hartford.funnybone.com/shows/> listing (732,527 bytes). The existing
Etix Rockhouse parser extracted 103 distinct performances, October 9, 2026
through June 27, 2027. The HTML contains explicit month/year separators,
individual Etix ticket IDs, single events and multiple-performance series.

Configure `platform=etix`, `scraper_key=etix`, priority 0, with that HTTPS public
listing as `source_url`. The generic Etix scraper already supports this path;
no new scraper or venue is needed. Preserve the existing Ticketmaster source.
The end-to-end smoke exposed a false block: the complete calendar includes
the normal `https://js.datadome.co/tags.js` vendor tag. Etix now ignores only
that exact script when Rockhouse cards are present and no CAPTCHA-delivery
marker exists; it rechecks all remaining HTML for block signatures. Real
challenge responses remain failures. The regression failed before this fix.

Two advertised music tribute brunches are excluded with exact
`metadata.excluded_event_titles` values; the remaining expected inventory is
101 comedy performances. The official descriptions describe music/drag tribute
performances rather than stand-up:

- [Hocus Pocus Tribute Drag Brunch](https://hartford.funnybone.com/event/hocus-pocus-tribute-drag-brunch/hartford-funny-bone/)
- [Dolly Parton Hard Candy Christmas Tribute Drag Brunch](https://hartford.funnybone.com/event/dolly-parton-hard-candy-christmas-tribute-drag-brunch/hartford-funny-bone/)

## Regression coverage

`tests/fixtures/hartford_funny_bone.html` retains selected native calendar cards
with decorative markup removed. `tests/test_hartford_funny_bone_coverage.py`
checks direct-source routing, multiple same-day performance IDs, the verified
Jeff Allen time and ticket, summer/winter Eastern offsets, year rollover,
explicit exclusions, and repeat-ingestion identity.

## Production verification

- Native end-to-end smoke returned **101 shows** after the two exclusions.
- Migration was applied twice in a rolled-back validation transaction: exactly
  one new source, original disabled source preserved, Eastern timezone and
  Jeff Allen time corrected, existing ticket IDs unchanged. The actual migration
  runner then applied the sole pending migration successfully.
- Two `make scrape-club CLUB='Hartford Funny Bone'` runs each persisted 101
  upcoming shows. All 101 dates, public event URLs and individual Etix purchase
  URLs matched the native snapshot. There were no duplicate date/room keys.
- The complete saved row sets (IDs, names, timestamps, URLs, rooms, ticket URLs
  and lineup counts) were identical across runs. Jeff Allen retained show ID
  **4942927**, with the verified 23:00 UTC timestamp and Etix performance 95937184.
- 97 performances have lineups. Existing generic title inference left two Lil Mo
  Mozzarella performances, Too Old To Be Lyin Comedy Tour and The Rich Guzzi
  Comedy Hypnosis Show without resolved lineup rows; show and ticket coverage
  is complete. No unsupported performer identities were added manually.
- Focused Etix suite: **155 passed**. Full scraper commit test gate passed.
