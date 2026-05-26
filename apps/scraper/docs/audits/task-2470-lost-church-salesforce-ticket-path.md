# TASK-2470: The Lost Church Salesforce Ticket Path Audit

Date: 2026-05-26
Club: The Lost Church, club 1047 (San Francisco, timezone America/Los_Angeles)
Ticketing platform: Salesforce Sites / PatronTicket

## Persisted ticket URLs

Club 1047 currently has 42 ticket rows. Every row is `type = 'General Admission'`,
has a non-null `purchase_url`, and uses exactly one URL shape:

- Base: `https://thelostchurch.my.salesforce-sites.com/ticket/`
- Fragment: `#/instances/<Salesforce instance id>`

There are 24 distinct Salesforce instance IDs across the 42 rows. The repeated IDs
appear on duplicated date rows for the same upstream PatronTicket instance and are
not a URL-shape problem.

Future rows as of this audit use the same shape. Examples:

| Stored show | Stored local date | Instance id |
|---|---:|---|
| Tony Sparks, Danny Dechi and Benjamin Steinberg | 2026-05-27 20:15 | `a0FUh0000088LU5MAM` |
| Hayden Johnson: Piss Queen | 2026-06-18 20:15 | `a0FUh000008UFt5MAG` |
| NEW DATE: Jenny Zigrino | 2026-10-17 20:15 | `a0FUh000006z5k5MAA` |

## How the URL reaches storage

The Lost Church is configured on the generic PatronTicket scraper:

- `scraping_sources.platform = 'patron_ticket'`
- `scraping_sources.scraper_key = 'patron_ticket'`
- `metadata.patronticket_venue_id = 'a0T6A000002eYckUAE'`

`PatronTicketExtractor.extract_events` reads `instance.get("purchaseUrl", "")`
from the Salesforce `fetchEvents` response and passes it into `PatronTicketEvent`.
`PatronTicketEvent.to_show` then uses that value as both the show page URL and the
fallback ticket `purchase_url`. No code in this scraper path reconstructs the URL
or strips the fragment.

## Live page behavior

I loaded three sampled stored URLs in headless Chromium so the PatronTicket SPA could
execute the client-side hash route.

| Instance id | Stored row | Rendered PatronTicket page |
|---|---|---|
| `a0FUh0000088LU5MAM` | Tony Sparks, Danny Dechi and Benjamin Steinberg, 2026-05-27 20:15 | `Buy: CANCELED Tony Sparks, Danny Dechi and Benjamin Steinberg - San Francisco - Comedy: Stand-up | Wednesday, May 27th, 2026 | Doors 7:30pm` |
| `a0FUh000008UFt5MAG` | Hayden Johnson: Piss Queen, 2026-06-18 20:15 | `Buy: Hayden Johnson: Piss Queen - San Francisco - Comedy: Stand-up | Thursday, June 18th, 2026 | Doors 7:30pm` |
| `a0FUh000006z5k5MAA` | NEW DATE: Jenny Zigrino, 2026-10-17 20:15 | `Buy: NEW DATE: Jenny Zigrino - San Francisco - Comedy: Stand-up | Saturday, October 17th, 2026 | Doors 7:30pm` |

Each sampled fragment opened the corresponding Lost Church purchase flow. The
`#/instances/<id>` fragment is the selector for a specific PatronTicket instance;
without it, the browser lands on the generic ticket app instead of a specific event.

## Conclusion

Fragment URL handling is correct for The Lost Church. The scraper persists the
Salesforce `purchaseUrl` with the `#/instances/<id>` fragment intact, and the live
PatronTicket app uses that fragment to render the expected purchase flow for the
sampled events. No remediation is needed for URL fragment handling.

Out-of-scope observation: the database contains repeated instance IDs on paired rows
for several events. That duplication is separate from the Salesforce fragment-path
handling audited here.
