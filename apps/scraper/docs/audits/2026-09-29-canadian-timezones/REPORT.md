# Canadian runtime timezone data — TASK-4073

## Evidence and scope

Checked 2026-09-29. Local Node 20.14.0 embeds tz2024a and ICU returns
UTC-7 for Edmonton and UTC-8 for Vancouver on December 1, 2026.
The installed pytz 2026.1.post1 has the same obsolete winter offsets.
System ZoneInfo already yields UTC-6 and UTC-7, demonstrating that providers
can disagree on the same machine.

Authoritative rules:
- [Alberta government](https://www.alberta.ca/albertas-new-time-system-abt):
  no November 2026 reset; permanent UTC-6.
- [British Columbia government](https://news.gov.bc.ca/releases/2026AG0013-000209):
  permanent Pacific daylight time after March 8, 2026.
- [IANA release notes](https://data.iana.org/time-zones/tzdb/NEWS):
  2026b introduces Vancouver permanent UTC-7; 2026c introduces Edmonton
  permanent UTC-6; 2026d additionally covers Inuvik. Tests assert offsets and
  wall times, not abbreviations, which depend on ICU/CLDR naming conventions.

The fix updates runtime/dependency selection and adds behavioral checks.
It does not migrate venue IANA names or rewrite stored UTC timestamps.

## Source offset audit

The official Next Stop Comedy pages for Big Beaver (show 4168931, club 11709,
March 13, 2027) and Leduc (show 4944800, club 12330, March 12, 2027) both display
**Show 7:00 p.m.**, with seating at 6:30 p.m.. Their JSON-LD still embeds
19:00-07:00. The stored instants exactly match that source offset, but map
to 20:00 under the current Edmonton rules. See source-offsets.json.

This establishes the advertised wall time, but runtime deployment must not
silently rewrite imported source instants. TASK-4119 owns guarded reconciliation,
source-ingestion replay, and reference/duplicate preservation. These events
remain unchanged in this task.

## Production baseline

Before deployment, production commit 0ce90af38 had READY deployment
 dpl_FGyd8ieTz94qvDeKKqBGsq47r4gW. Raw public show-page metadata already
renders December 3 Edmonton and Vancouver samples at 8:30 p.m. with their current
correct offsets. Leduc renders 8 p.m.; Big Beaver still renders 7 p.m. MST.
This mixed cached output is not proof that all production runtime data is
obsolete. The production-before.json snapshot records exact UTC values,
metadata and API responses for comparison after deployment.

## Remaining client-side concern

A server runtime update cannot replace timezone data in older browsers.
Client show cards and ticket controls also call formatShowDate. TASK-4120
tracks consistent server/client rendering under stale browser ICU.

## Runtime verification

Node 24.21.0 embeds ICU 78.3 / IANA 2026c. Run `npm run verify:timezones`
from apps/web to check 14 native Intl cases. Python uses locked pytz 2026.4
and tzdata 2026.4; production setup exports `PYTHONTZPATH=""` so ZoneInfo
uses the wheel. Run `python scripts/verify_timezone_data.py` from apps/scraper
to check 28 real-library cases. Historical winters and US DST controls remain
covered. Builds fail before migrations if Node data is stale.

The actual formatShowDate suite passes 25 tests under Node 24.21.0; Node
20.14.0 fails six. The Python timezone and datetime utility suites pass
32 tests with the updated wheels. The 19-case timezone suite fails 11 tests
with old pytz 2026.1.post1 / tzdata 2026.2. Test runs use TZ=UTC and isolated
runtimes; shared developer dependencies were not modified.

The read-only Timezone runtime check workflow verifies the same composite
setup used by production scrapers. Production deployment and unchanged UTC
values must be verified after merge and recorded in TASK-4073's progress.
