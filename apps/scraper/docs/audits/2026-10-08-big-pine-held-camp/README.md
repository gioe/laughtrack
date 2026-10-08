# TASK-4137 — Big Pine occurrence 522192: continued hold

## Decision

**Preserve show 522192 unchanged. No production correction or deletion is
supported by the retrieved evidence.** Native identity 356284 is a strong link
to the current education product, but the conflicting historical dates remain
unresolved. This completes the task's explicitly permitted continued-hold branch;
it does not establish which stored date is correct.

| Evidence | Identity | Date |
| --- | --- | --- |
| Fresh production row | Club 573 / show 522192 / URL `/shows/356284` | May 10, 2026, 16:00 UTC |
| October 5 and October 7 committed inventory | Same row and URL | May 10, 2026, 16:00 UTC |
| October 7 native detail | Venue 553 / show 356284 / event 130312 | May 3, 2026, 16:00 UTC |
| Fresh October 8 native detail | Same venue/show/event; inventory 765044 | May 3, 2026, 16:00 UTC |

The fresh native detail's local offset is `2026-05-03T09:00:00-07:00`.
Normalizing that instant to UTC cannot explain a seven-day difference.
Its inventory explicitly admits workshops and panels. That classification comes
from admission inventory, not the generic SUMMER COMEDY CAMP title.

## Evidence and limits

[source-evidence.json](source-evidence.json) contains the fresh native response,
the actual 16-item current-feed count and IDs, request URLs, and timestamped
public-page/archive observations. Native requests used the scraper's configured
`SeatEngineClient`; JSON was parsed directly. HTML used `HttpClient` with
curl-cffi and the normal browser fallback. Auth headers and private database
relationships are not committed.

The exact public occurrence URL now renders the current festival listing; it
does not supply the historical camp date. A speculative legacy SeatEngine
hostname renders vendor marketing and provides no supporting occurrence data.
The exact-URL Wayback CDX request timed out; the availability API returned 429.
Neither failure proves that no archive exists.

A search-index preview for the festival's
[older event URL](https://www.bigpinecomedyfestival.org/events/109194) mentions
May 9/10 camp admission. It supplies no exact native occurrence binding or
reschedule history. Opening that URL resolves to a later upcoming calendar
without May 10. The preview is a lead, not sufficient identity evidence.

The [October 7 audit](../2026-10-07-big-pine-remaining/README.md) already held
this row for the same mismatch. The October 5 inventory independently records
the stored May 10 value. These database captures are historical observations
of our data, not independent proof of the provider's historical schedule.
No retrieved dated native capture or explicit provider history links May 10
and May 3 for occurrence 356284. We cannot distinguish rescheduling, changed
source data, or a stored-date error from these observations.

## Preservation boundary

No repair, cleanup dry run, scraper persistence, source change, visibility change,
or date backfill is performed. The previous 19-ID and 36-ID cleanup scripts
remain frozen. Their old recovery files are not used as current before-images.

The new read-only verifier covers all 17 retained festival rows and their seven
dependent tables, all club 573 clicks including detached history, club visibility,
sources 360/3126/7146, and platform targets 1/2. No recovery backup is required
because this task does not perform database writes. Verification results are
recorded separately in this audit directory.

Reopen the disposition only when a dated native capture or explicit provider
history binds occurrence 356284 to the conflicting schedules, or an authoritative
historical record resolves the stored row's actual occurrence. Do not treat a
redirect, feed absence, matching title, or current workshop classification alone
as proof permitting cleanup.
