# Denver Comedy Lounge price evidence — TASK-4102

Verified 2026-10-05 with the scraper's PlaywrightBrowser.fetch_html against
https://denvercomedylounge.com/shows and the first two dated detail pages:
- /shows/friday-7pm-2026-10-09: Event start 2026-10-09T19:00:00-06:00.
- /shows/friday-9pm-2026-10-09: Event start 2026-10-09T21:00:00-06:00.
Both exact-URL Events are Scheduled, with USD 21 General Admission and USD 45
VIP Offers, InStock, validFrom 2026-07-10T07:00:39Z. React show data says
on_sale, soldOut false, cancelled false. GA is standard seating; VIP includes
front two rows plus a half flight of premium sake. These are ticket-tier prices,
not table totals; the sake-sharing suggestion does not make VIP a two-ticket offer.
Fees/taxes are not itemized in these offers: $21 is venue-advertised admission,
not a verified checkout total. No checkout or purchase was performed.

The retained denver_comedy_lounge-1.html / denver-event-rsc.json target is
Friday October 2 at 19:00 Denver time (audit show 3790700), now expired.
At the fixed September 27 audit time it has the same GA21/VIP45 structure.
The original literal JSON-LD extractor returned None on that HTML; the shared
RSC decoder reveals the Event. Regression tests freeze audit time and separately
reject the expired page at current time. Live October 9 page recovers 21.

Implementation recovers only exactly matched dated Event General Admission.
VIP package prices, relatedShows, generic from-$20 copy, business priceRange,
unavailable offers, conflicting events and unverified payloads remain excluded.
Unknown detail prices retain the listing show and its unknown-price ticket.
The listing yielded 65 parseable shows; its separately named Jennifer Gable slug
was unparseable by the existing listing parser, outside this price-only change.
No production rows were mutated and the historical snapshot is not an inventory target.
