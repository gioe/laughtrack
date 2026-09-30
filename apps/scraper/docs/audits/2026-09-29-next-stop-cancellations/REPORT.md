# Next Stop Comedy cancellation audit — TASK-4074

## Source evidence

On 2026-09-29, fetched all 1,562 distinct URLs attached to 1,599 future
Next Stop Comedy shows, plus the now-past original Cedar St sample. Used
HttpClient.fetch_html with the scraper's curl-cffi Chrome session and its
normal browser fallback, with six concurrent requests. Each source record
contains its URL, capture time, HTML SHA-256 and unmodified JSON-LD identity,
time and status fields. No production records changed during this audit.

All twelve original samples still explicitly say EventCancelled. Eleven
remain future; Cedar St show 4944522 occurred on September 26 UTC and stays
outside the future repair. Thirty additional future canceled shows were
found, yielding **41 confirmed future cancellations** across exact matching
source URLs, UTC instants and next_stop_comedy attribution. All 42 canceled
samples, including the past one, were emitted by the pre-fix extractor.

Of 1,600 audited stored rows, 1,494 have an exact matching scheduled source,
42 have an exact matching canceled source, and 64 remain unresolved. The
64 URLs comprise 55 canonical URL changes and nine fetch/parse failures.
They are not cancellation evidence and must not be removed by this repair.

- `db-before.json`: complete audited cohort, with stored identities and UTC values.
- `sources.jsonl`: all 1,563 fetched URLs and their source evidence.
- `cancelled.json`: exact-source canceled cohort, including future/past disposition.
- `unresolved.json`: retained rows requiring separate identity/rescheduling research.

## Preservation requirements

The 41 future canceled shows have 41 tickets, 40 lineup items, 92 tags and
924 ticket-click records. They have no saved-show or sent-notification rows
at audit time. A DELETE would null the click records' show_id foreign keys;
therefore the repair must retain shows and all related records, mark explicit
cancellation separately, and exclude canceled shows from public discovery.
Missing pages, redirected URLs and partial listing coverage do not establish
cancellation. Active show dates and venue identities remain unchanged.

## Verification

The focused Next Stop suite passes 34 tests after explicit cancellation
filtering. Cases cover canonical HTTPS/HTTP and bare Schema.org status,
scheduled, rescheduled, missing and unknown status, mixed graph nodes,
failed detail fetches, and exclusion before venue upsert. Nearby-event
timezone isolation remains covered for uncanceled pages.

Public filtering, guarded reconciliation and production verification are
recorded below when complete.
