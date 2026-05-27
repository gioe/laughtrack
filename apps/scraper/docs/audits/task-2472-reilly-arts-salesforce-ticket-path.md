# TASK-2472: Reilly Arts Center Salesforce Ticket Path Audit

Date: 2026-05-26
Club: Reilly Arts Center, club 2368 (Ocala, FL, timezone America/New_York)
Ticketing platform: Salesforce Sites / PatronTicket
Official site: https://reillyartscenter.org

## Persisted ticket URLs

Club 2368 currently has 2 ticket rows (matching `clubs.total_shows = 2`). Both rows
are `type = 'General Admission'`, have a non-null `purchase_url`, and use exactly one
URL shape:

- Base: `https://reillyartscenter.my.salesforce-sites.com/ticket/`
- Fragment: `#/instances/<Salesforce instance id>`

Both instance IDs are distinct — there is no duplicate-instance shape concern here.

| Stored show | Stored UTC date | Local (America/New_York) | Instance id |
|---|---|---|---|
| Jim Breuer: Find The Funny | 2026-05-15T23:30:00+00:00 | Fri 2026-05-15 7:30 PM EDT | `a0FV1000002hhzpMAA` |
| Jamie Lissow - The Better Off Dad Comedy Tour | 2026-08-30T23:30:00+00:00 | Sun 2026-08-30 7:30 PM EDT | `a0FV1000002kgr7MAA` |

## How the URL reaches storage

Reilly Arts Center is configured on the generic PatronTicket scraper
(`scraping_sources` id 2300, priority 0, enabled):

- `scraping_sources.platform = 'patron_ticket'`
- `scraping_sources.scraper_key = 'patron_ticket'`
- `scraping_sources.source_url = 'https://reillyartscenter.my.salesforce-sites.com/ticket'`
- `metadata.patronticket_venue_id = 'a0TV100000GFLfpMAH'`

A second `scraping_sources` row (id 1376, `tour_dates`, priority 1) is disabled — it
was the Steve-O tour-date discovery fallback, replaced by the verified PatronTicket
scrape on 2026-05-13 (`metadata.tour_date_onboarding_replaced`).

`PatronTicketExtractor.extract_events`
(`src/laughtrack/scrapers/implementations/venues/patron_ticket/extractor.py:163`)
reads `instance.get("purchaseUrl", "")` from the Salesforce `fetchEvents` response
and passes it into `PatronTicketEvent`. `PatronTicketEvent.to_show`
(`src/laughtrack/core/entities/event/patron_ticket.py:63`) then uses that value as
both the show page URL and the fallback ticket `purchase_url`
(`ticket_url = url or self.purchase_url`). No code in this scraper path reconstructs
the URL or strips the `#/instances/<id>` fragment. This is the same path audited for
The Lost Church (TASK-2470) and UP Comedy Club (TASK-2468).

## Live page behavior

I loaded both sampled stored URLs in a real browser (Playwright) so the PatronTicket
SPA could execute the client-side hash route.

| Instance id | Stored row | Rendered PatronTicket "Buy" page title |
|---|---|---|
| `a0FV1000002hhzpMAA` | Jim Breuer: Find The Funny, 2026-05-15 7:30 PM EDT | `Buy: Jim Breuer: Find The Funny - Friday, May 15, 2026, 7:30 PM` |
| `a0FV1000002kgr7MAA` | Jamie Lissow - The Better Off Dad Comedy Tour, 2026-08-30 7:30 PM EDT | `Buy: Jamie Lissow - The Better Off Dad Comedy Tour - Sunday, August 30, 2026, 7:30 PM` |

Each sampled fragment opened the corresponding Reilly Arts Center purchase flow, and
the rendered show name + date/time matched the stored Eastern-time value exactly.
Navigating to a different `#/instances/<id>` re-rendered the SPA to that show — the
fragment is the instance selector. Without it, the browser lands on the generic
PatronTicket landing instead of a specific event.

## Conclusion

**Fragment URL handling is correct for Reilly Arts Center — no remediation needed.**
The scraper persists the Salesforce `purchaseUrl` with the `#/instances/<id>` fragment
intact, and the live PatronTicket app uses that fragment to render the expected
purchase flow for both stored events, with show dates matching our persisted data.
Nothing in our URL parsing or rendering collapses the fragment.
