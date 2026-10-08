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

## Preservation decision pending

The 36 upcoming rows have 36 tickets, 29 tag links, zero lineup entries and
134 ticket-click records. They have no saved-show, sent-notification or feature
snapshot references in this capture. The entire venue has 1,694 click records.

Existing cleanup scripts delete selected shows and rely on the click foreign
key's SET NULL behavior: click records survive but their show links do not.
TASK-4143 currently requires preserving user and analytics relationships. The
operator has been asked whether to add show-level exclusion support that retains
those links or explicitly allow existing cleanup with detached click records.
No production repair has been applied. Fresh full before-images and guarded
recovery will be required for the chosen approach; this evidence snapshot is
not an executable deletion plan.
