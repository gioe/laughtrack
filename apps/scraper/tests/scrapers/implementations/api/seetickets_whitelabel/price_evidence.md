# SeeTickets calendar price evidence — TASK-4093

Read-only fetch of https://portcomedy.com/calendar/ on 2026-10-04 through
`HttpClient.fetch_html` with curl-cffi Chrome impersonation succeeded (281463
characters). No checkout, persistence, or additional detail requests were used.

The official dated calendar supplies provider event IDs and local showtimes.
Its parallel list supplies `.event-title a`, `.event-date`, `.see-showtime`,
and a scoped `.price`. Current positive matches:

| Provider ID | Baltimore local time | Advertised admission price |
| --- | --- | --- |
| 682822 | 2026-10-04 20:00 | $29.00-$39.00 |
| 700242 | 2026-10-08 20:00 | $20.00 |
| 679250 | 2026-10-09 19:30 | $25.00 |
| 679265 | 2026-10-09 21:45 | $25.00 |

There are 132 authoritative calendar performances, nine list price nodes,
four positive matches, and five $0.00 placeholders. The remaining 128
performances have no verified positive price in this response. These are
source matches, not a claim that 132 database tickets were repaired.

The targeted prices are advertised admission prices next to the event title,
21+ age restriction, venue, and Buy Tickets link. No package or multi-person
unit is stated. Currency is contextual USD from The Port Comedy Club in
Baltimore, Maryland and its US SeeTickets storefront; the spans do not contain
an explicit ISO currency code. Neither fee inclusion nor fee amounts are
stated. A range is a starting advertised admission price, not a guaranteed
all-in checkout price or evidence of inventory for each tier. Buy Tickets is
the observed availability signal for these matches; no inventory count is
published. Sold Out evidence must be handled per event, never globally.

The retained 2026-09-27 audit response in
`docs/audits/2026-09-27-price-extraction/ticketing/seetickets_whitelabel-11482-listing.html`
reproduces the omission: the existing parser emits 144 performances with all
ticket prices unknown. Three exact positive matches are provider IDs 682818
(Oct 1 20:00), 682820 (Oct 2 19:30), and 682823 (Oct 2 21:45), all $29-$39.
The audit's IDs 3434328, 3434329, and 7416212 are database show IDs, not
provider IDs. Those historical performances are absent from the current
calendar; their recovery evidence is historical only. The other 134 tickets
in that fixed 137-ticket cohort remain unresolved by the three historical
matches. Do not extrapolate either snapshot to current inventory.

Join requirements: exact provider host and ID, matching list month/day/weekday
and showtime against the calendar's explicit year. Never join by title or
position. Conflicting repeated list evidence is unknown. Parse only a full
positive dollar price/range from the scoped price span; zeros, unrelated dollar
text, ambiguous dates, missing buy links, or mismatched identities remain
unknown. Preserve the source range in the ticket label and keep fees unknown.
