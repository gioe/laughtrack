# Ticket Tailor price evidence — TASK-4095

Verified 2026-10-04 using `TicketTailorScraper._fetch_listing` with the venue's
Referer and its native curl-cffi fingerprint retries. No database writes.

The retained September 27 audit contains 51 unknown ticket rows. Four dated
performances have matching detail evidence; the other 47 remain unresolved by
this evidence. This is a historical lower bound, not a current recovery count.

| Detail | Retained performance (local offset) | Named USD offers |
| --- | --- | --- |
| `/events/westrivercomedyclub/2363785` | Oct 2 19:30−06, Oct 3 19:30−06, Oct 4 17:00−06 | Tier 1 (Table for 2): 50; Tier 2 (Table seating): 20; General Admisson Row Seating: 15 |
| `/events/continentalclub/2347556` | Nov 5 19:00−08 | Early Bird: 24.75; General Admission: 28; VIP: 38.75 |

Each retained Event has its own startDate and named Offer array. Event.url is
absent; Offer.url establishes identity. All these offers declare USD and
InStock. Fees/taxes are unspecified, so these are advertised offer prices, not
verified checkout totals. The table-for-two price is $50 per package, never
$25 per person. Table seating does not explicitly state its admission unit;
retain that amount as labeled evidence without using it as an individual minimum.

Current native fetch results:

- `https://www.tickettailor.com/events/westrivercomedyclub/2363785` fetched
  successfully (36,125 HTML characters). It now contains only Oct 4 **18:00−06**,
  with the same three amounts. The canonical URL and Offer URLs now use
  `events.westrivercomedy.com` with the identical account/event path. None of
  the three historical West River times matches this current response.
- `https://events.oaklandcontinentalclub.com/events/continentalclub/2347556`
  fetched successfully (36,021 HTML characters), retaining Nov 5 19:00−08 and
  all three USD/InStock offers. This is **one current matched historical
  performance**; three historical West River matches are now unresolved.

The implementation must match exact timezone-aware performance instants and
offer URLs, allowing a custom canonical host only when the fetched document
declares it with the identical account/event path. Unmatched dates, failed
fetches, missing currency, zero placeholders and unsupported currency must
remain unknown. Source availability and named amounts survive conversion.
Because the shared minimum-price calculation does not exclude packages or
unavailable tickets, their source amounts remain in labels but not positive
numeric Ticket prices. No shared pricing schema change is part of this task.
