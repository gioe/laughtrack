# BATSU dated reservation recovery — 2026-10-01

TASK-4085 follows the conservative TASK-4054 audit. The public Tock dated
calendar now supplies positive evidence for 57 Chicago performances and 77 NYC
performances. It does not establish that omitted performances were cancelled.

## Source and transport

Storefronts are https://www.exploretock.com/batsu-chicago (business 29114,
club 11073/source 6842) and https://www.exploretock.com/batsunyc
(business 27051, club 16048/source 7643). Published Tock client assets identify
POST /api/consumer/calendar/full/v2 as a public calendar read. This does not
create a reservation, ticket hold, cart or purchase.

The actual shared HTTP stack recovered the storefronts but a separate calendar
request hit Cloudflare. The normal solver reported that challenge HTML was
required. Passing fresh challenge HTML, preserving one sticky residential proxy
session, and fetching the calendar in the same cleared browser context recovered
HTTP 200 binary responses: 40,916 bytes Chicago and 61,100 bytes NYC. Anonymous
session headers remain inside the browser and are not retained in this audit.
The compact dated-group artifacts record raw-response SHA-256 hashes and public
fields only. Raw Redux state and its session tokens are intentionally excluded.

The published proto2 request is MessageSet field 60331 with an empty payload
(hex daba1d00). Actual responses use SingleResponse → GenericMessage →
MessageSet field 60686 (ConsumerFullCalendarV2), not the legacy 60192 schema.
V2 maps business days to dates and dated ticket groups. Each group's time and
startTimeSecs agree with its date key in the venue timezone, including November
DST. Prices are attached to the group's own ticket type. Ticket tiers represent
one performance, not separate rooms. Captured priceCents are base prices; this
report does not claim fee-inclusive checkout prices.

## Inventory comparison and conservative reconciliation

inventory-before.json contains all 389 original show records; 194 were future
at the comparison cutoff. calendar-comparison.json lists every unmatched future
row, and the two dated-group artifacts retain all 269 public ticket groups.

| Venue | Original total | Future rows | Dated matches | Unconfirmed |
|---|---:|---:|---:|---:|
| Chicago | 150 | 72 | 57 | 15 |
| NYC | 239 | 122 | 77 | 45 |

All 134 dated performances already have matching stored instants. Chicago's
12 Friday 22:00 performances from October 2 through December 18 are confirmed
exceptions to the ordinary weekly schedule used in the earlier audit. Removing
all late shows based on that schedule would have deleted valid performances.

The response includes some zero-availability groups but also open dates with no
groups (Chicago December 3; NYC October 13, November 5/10/17, December 9/16).
Consequently, absence is not cancellation evidence. No time change or deletion
is justified for the 60 unconfirmed records. There is no destructive SQL
migration: reconciliation updates only positively dated performances through the
normal identity-preserving upsert. Recurring reservation coverage is always
marked partial so its omissions cannot authorize stale cleanup. Existing GA
experiences continue to use their own explicit dated schedules.

## Verification

Focused regression tests cover the captured date/epoch associations, ticket-tier
consolidation, sold-out records, source identity, malformed/error responses, and
partial-coverage cleanup protection. Shared transport tests cover same-context
requests, origin/identity checks, response bounds, timeout cleanup and fresh
challenge HTML. Scheduled-runner and production results are recorded below after
verification.

The completed scraper's read-only live run recovered exactly 57 Chicago and 77
NYC shows. live-preview.json records every transformed show and its tickets.
Neither run saved data; both reported partial coverage to block reconciliation.

Four reservation performances expose only one tier in the snapshot. The scraper
marks their ticket coverage partial as well: the ticket writer refreshes observed
tiers but preserves omitted existing tiers. This prevents a second cleanup path
from treating availability omissions as ticket deletions. Complete ticket feeds
retain their existing stale-tier cleanup behavior.

## Scheduled runner and production verification

Code commit a6ebf9f8ce06434eaa6ed3ffce8bb20eba24ea6a passed the full scraper
commit gate (77.9 seconds). Both Ubuntu scheduled-stack verification runs used
the same browser, residential proxy and solver configuration as nightly:

- Chicago: [36909958003](https://github.com/gioe/laughtrack/actions/runs/36909958003),
  57 shows and 112 affirmed ticket tiers processed.
- NYC: [36909983250](https://github.com/gioe/laughtrack/actions/runs/36909983250),
  77 shows and 150 affirmed ticket tiers processed. Browser installation was
  slow; the job ultimately succeeded without a rerun.

The production comparison verifies all 389 original show IDs and 774 ticket IDs
survive. Exactly 134 positively dated performances were refreshed in place with
262 observed ticket tiers. The other 255 records, including all 60 unconfirmed
future listings and their tickets, are byte-for-byte unchanged in the audited
fields. No shows were added or removed, and all lineups remain empty. The four
unobserved ticket tiers on refreshed reservation performances were preserved.
Existing keyed upserts refreshed records without duplicating their identities;
no timestamp-moving or deletion migration was warranted by the dated evidence.
production-verification.json contains the final records and checked counts.

This is a recurring scraper fix for the two BATSU sources, not a one-off data
patch. It does not claim complete reservation coverage or cancellations for the
60 listings that the public snapshot cannot affirm.
