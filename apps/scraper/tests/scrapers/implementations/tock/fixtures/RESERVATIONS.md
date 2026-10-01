The 20261001 fixtures derive from successful public `/api/consumer/calendar/full/v2`
responses captured in the venue's challenge-cleared browser context on October 1,
2026. They are not handwritten calendars.

The binary fixtures retain the original protobuf envelope and dated map structure,
with only fields consumed by the parser retained. Unrelated fields were removed
using the field numbers from the same day's published explore.js schemas. Public
HTML fixtures retain only business identity and public experiences, explicit GA
schedules, and venue locations; all session/auth/CSRF data was excluded.

Chicago: 119 ticket groups consolidate to 57 reservation performances.
NYC: 150 ticket groups include 75 reservation performances plus 2 explicit GA
performances (the GA dates continue through the existing GA parser).

Prices are base cents per ticket, not fee-inclusive advertised totals. Zero
available tickets do not remove performances. Missing dates/groups are not proof
of cancellation; the ingestion path always disables stale reconciliation.
