# TNEW admission evidence — TASK-4094

Read-only verification on 2026-10-04 used HttpClient.fetch_html with the
scraper's curl-cffi Chrome session. No seats were selected or reserved and no
checkout/persistence operation was performed.

## Groundlings

The retained audit page
`docs/audits/2026-09-27-price-extraction/ticketing/tessitura_tnew-8836-detail.html`
identifies production 17753 / performance 18662, September 27 2026 7:30PM in
Los Angeles (September 28 02:30 UTC). It advertises Adult Ticket in General
Admission at USD 27 total: 25 ticket + 2 fees. Currency is explicit in
`tnew.app.init` (`iso4217CurrencyCode: USD`). Zone 37 has 78 available and
enabled quantities 1–20. The synthetic zone 0 repeats prices without its own
inventory proof; it must not be counted. Each selector quantity is one ticket.

This is the one historical matched recovery in the fixed 92-ticket audit
cohort (show 3503404, ticket 3918380). Its original URL now returns HTTP 404:
https://purchase.groundlings.com/17753/18662 . It is not a current recovery.
The current listing loads, but the exploratory production API POST returned
non-JSON; no current Groundlings inventory count is asserted.

## Gallo

https://tickets.galloarts.org/11397/11398 currently verifies October 16 2026
7:30PM Los Angeles time, matching historical show 5101652 / ticket 5766555.
The main page contains pricing configuration only and cannot establish a
buyable minimum. Its explicit “Purchase Best Available Seating” link goes to
https://tickets.galloarts.org/11397/11398?z=0 . That selector was fetched through
the same stack and retained in `gallo_available.html` (relevant scripts, date,
and form; anonymous session data and request-verification token removed).

The current selector proves one Regular admission in Parterre, zone 327:
USD 68 total = 59 ticket + 9 mandatory fees, availability count 1, enabled
quantity 1. All other eight zones have zero inventory and disabled inputs.
The advertised 39 base + 9 fee section is therefore not buyable in this
snapshot. Synthetic zone 0 advertises 48–108 but has no independent inventory
and must be ignored. Currency is explicitly USD. Prices are per ticket, not
per table or group. These are advertised mandatory fees, not a claim about
any additional order-level checkout charges.

The separate 50 talkback and 150 meet-and-greet are add-ons requiring admission
and must never become admission prices. This current sample establishes one
matched recovery, not a full-cohort audit; 91 of the fixed 92 tickets remain
unverified by this current sample. Historical and current counts are separate.

## Rules verified

Require matching host, production/performance IDs in URL, product model and
form, exact rendered date/time against the listing, explicit USD, actual
available zone and enabled positive quantity, and a named admission tier.
Preserve total/base/fee labels. Price-only failures, zero placeholders,
unsupported currency, identity conflicts, unavailable seats, add-ons and
seat-map configuration without availability remain unknown. Follow at most
one identity-matched best-available link per detail and bound the whole phase.
