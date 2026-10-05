# Odoo registration evidence — TASK-4096

Verified 2026-10-04 through `OdooEventsScraper._fetch_configured_html`, using
the scraper's configured HTTP stack. Read-only requests; no registrations or
database updates were performed.

The retained September 27 audit has 57 unknown ticket rows. One dated match
(ticket 5158255 / show 4577194) has recoverable evidence: Comedy Plex Presents:
Matt Torres, October 2 00:30 UTC (October 1 19:30 America/Chicago), advertised
USD 15 per admission. The remaining 56 rows are unresolved by this evidence.
These are historical lower bounds, not current inventory targets.

The retained `odoo_events-9092-detail.html` has an Event with no scoped offers.
Its detached `form#registration_form` posts to the exact event's
`/event/comedy-plex-presents-matt-torres-926/registration/new`; the public page
is `https://www.comedyplex.com/event/comedy-plex-presents-matt-torres-926/register`.
The cover's event.event ID is 926. Within the registration row, the named tier
Matt Torres has price 15.0, currency USD, InStock and an enabled quantity
selector with options 0–9. Quantity is the number of admissions purchased;
it does not divide or multiply the unit price. The initially disabled submit
button is JavaScript-controlled and does not mean sold out.

Current native fetch of that exact URL returned 60,734 HTML characters and
the same Event/date, but **no registration form**. It is now a past show.
Current recovery for this historical match is therefore zero; its price must
remain unknown when only today's page is available.

A current listing/detail check confirmed a second Odoo layout:
`https://www.comedyplex.com/event/oprf-alumni-comedy-showcase-976/register`
(68,382 HTML characters), October 10 21:00 UTC / 16:00 Chicago. Its exact-event
form contains `.o_wevent_ticket_selector` rows rather than the single-ticket
layout. `Advace Tickets` (source spelling) is USD 20 with enabled quantities
0–9. `Day Of Tickets` is USD 25, has no quantity selector, and says sales start
October 10 at noon Chicago. Only the advance tier is currently purchasable.
These rows omit explicit schema availability; enabled positive quantities
supply the advance tier's availability evidence. This is a separate current
source check, not another matched row from the fixed audit cohort.

Fees/taxes are unspecified on both sources; prices are advertised admission
amounts, not verified checkout totals. The current showcase description also
states a two-drink minimum per person, whose cost is unspecified and excluded.

Odoo-only association must require the same origin/event path for the fetched
page, Event identity and registration action. Reject unrelated forms and
ambiguous Event scopes. Keep each named row's price/currency/quantity together;
retain package amounts without treating them as individual minima. Zero,
invalid, non-USD and non-purchasable prices stay numerically unknown. Shared
microdata extraction must continue to return no offers for the detached form.
