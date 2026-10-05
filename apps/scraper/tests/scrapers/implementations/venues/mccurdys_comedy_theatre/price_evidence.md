# McCurdys venue price evidence — TASK-4099

Verified October 5, 2026 with McCurdysComedyTheatreScraper.fetch_html, the native
scraper HTTP stack. No Etix request, purchase or production data update is needed.

The retained September 27 audit matches two unknown tickets:

| Show / ticket | Etix performance ID | UTC performance | Venue text |
| --- | --- | --- | --- |
| 2953407 / 3207388 | 53957625 | September 28 00:00 | Tickets $26 |
| 1178321 / 1125049 | 55715949 | September 27 21:30 | Tickets $26 |

The first is Drag Queen Bingo Extravaganza, September 27 at 8 PM local;
the second is Wyatt Cote, September 27 at 5:30 PM local. Each retained detail
has one performance row and two identical responsive copies of Tickets $26
beside its title inside .content.vevent. The price is advertised admission
in US dollars at this Sarasota, Florida venue, not verified checkout total.
The fixed-snapshot recoverable lower bound is two tickets. Unsampled tickets
remain unresolved; these examples do not establish prices for other dates.

Current verification fetched https://www.mccurdyscomedy.com/shows/ and its
first two detail links. /shows/show.cfm?shoID=83 advertises Carmen Ciricillo,
Wednesday October 7 at 7 PM America/New_York (23:00 UTC), performance 85920037,
with identical desktop/mobile Tickets $26 text and an enabled BUY link.
The other page, shoID=407, exposes no performance rows or admission price.
This confirms the live venue shape separately from the historical cohort.

The source establishes advertised individual admission and an available BUY
link, not seat inventory or checkout fees. House rules separately describe
a two-item food/drink minimum and 18% gratuity on checks. Neither is admission.
Do not fetch Etix merely to extract this venue-published amount, add fees,
or claim the amount is all-inclusive.

Association rules: pair date and ticket ID within one performance li. A
row-specific price belongs only to that row. A title-level price is usable
only for a single unambiguous listed performance in that event container.
Multiple dates without row prices, conflicting responsive prices, variable
tiers/ranges, missing/zero/invalid prices and non-USD labels remain numerically
unknown. Preserve scoped advertised wording without guessing a minimum.
