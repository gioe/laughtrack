# Barrel Room upcoming non-comedy cohort — TASK-4143

Fresh October 8, 2026 inspection confirms 36 future club 88 shows still eligible
for public discovery after source 77 was disabled. All 36 match native SeatEngine
series links by numeric show ID and exact date/time in America/Los_Angeles.
The five series explicitly describe musical programming: 15 piano shows, eight
Sunday jams, seven Tuesday jams, three bass-DJ nights, and three musical open mics.
No ambiguous upcoming row was found. Native evidence establishes genre; this
review does not claim that checkout remains active or that the events are cancelled.

`native-review.json` records every exact stored ID/URL/date, matching native
occurrence, series URL, capture timestamp and HTML hash. Fetching used the
scraper's own HTTP stack. Individual series pages lack the Classic extractor's
calendar JSON, so occurrence dates were read from the native date headings and
show links. Local native clocks were converted using America/Los_Angeles and
asserted equal to stored UTC timestamps, including November's offset change.

Preserve the other 287 historical rows, including all ten **Inside Jokes -
crowd-driven comedy** shows. Source 77 remains disabled. Do not infer that the
venue never hosts comedy, hide its entire history, or mark musical shows as
source-cancelled.

## Approved cleanup and preservation

The 36 upcoming rows have 36 tickets, 29 tag links, zero lineup entries and
134 ticket-click records. They have no saved-show, sent-notification or feature
snapshot references in this capture. There are 1,694 clicks still attached to
venue shows, plus 32 already-detached venue clicks; the repair preserves all 1,726.

Existing cleanup scripts delete selected shows and rely on the click foreign
key's SET NULL behavior: click records survive but their show links do not.
The operator explicitly selected **cleanup**: remove the 36 verified shows and
their 36 tickets/29 tag links, retain all click records with only the 134 retiring
show links cleared. Historical shows and their references remain unchanged;
club identity/visibility and disabled source 77 stay unchanged. Update the club's
stored show count to the surviving count. Any newly discovered saved-show,
notification, feature-snapshot or lineup reference on a retiring show aborts.

The dated archive script pins this exact native manifest, verifies a fresh
`reviewed-plan.json` against full schema and row hashes, and writes new private
mode-0600 before/after recovery files before commit. Detached clicks remain in
the guarded cohort by club ID. Recovery restores exact original shows, ticket/tag
links and click associations only if the entire affected after-state still matches.
Neither a cancellation flag nor a venue-wide visibility change is used.

Before apply, 18 local PostgreSQL tests passed. A production rehearsal performed
cleanup, verified repeat safety, restored the entire original state exactly,
and rolled back the transaction. The public club-shows API independently returned
all 36 reviewed IDs before cleanup. The full commit gate has a pre-existing
missing-tzdata collection error (8,210 collected); three clean-HEAD runs reproduced
it without flakiness or default-branch divergence. No full-suite pass is claimed.

Execution outcome and private recovery locations are recorded in verification.md.
